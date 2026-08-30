import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get all available cases
router.get('/', async (req, res) => {
  try {
    const cases = await prisma.case.findMany({
      where: { 
        isActive: true,
        OR: [
          { isLimited: false },
          { 
            isLimited: true, 
            limitedUntil: { gte: new Date() } 
          }
        ]
      },
      include: {
        items: {
          include: { item: true }
        }
      }
    });

    res.json(cases);

  } catch (error) {
    console.error('Get cases error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get specific case details
router.get('/:id', async (req, res) => {
  try {
    const caseData = await prisma.case.findUnique({
      where: { id: req.params.id },
      include: {
        items: {
          include: { item: true }
        }
      }
    });

    if (!caseData) {
      return res.status(404).json({ error: 'Case not found' });
    }

    res.json(caseData);

  } catch (error) {
    console.error('Get case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Open a case
router.post('/:id/open', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const caseData = await prisma.case.findUnique({
      where: { id: req.params.id },
      include: {
        items: {
          include: { item: true }
        }
      }
    });

    if (!caseData) {
      return res.status(404).json({ error: 'Case not found' });
    }

    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Check if user has enough balance
    const userBalance = caseData.currency === 'STORM_COINS' ? user.balance : user.premiumBalance;
    if (userBalance < caseData.price) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }

    // Deduct cost
    await prisma.user.update({
      where: { id: decoded.userId },
      data: {
        [caseData.currency === 'STORM_COINS' ? 'balance' : 'premiumBalance']: {
          decrement: caseData.price
        }
      }
    });

    // Calculate drops based on drop rates
    const drops = calculateDrops(caseData.items);
    const droppedItems = drops.map(drop => drop.item);
    
    // Calculate total value
    const totalValue = droppedItems.reduce((sum, item) => sum + item.basePrice, 0);

    // Add items to inventory
    for (const item of droppedItems) {
      await prisma.inventoryItem.upsert({
        where: {
          userId_itemId: {
            userId: decoded.userId,
            itemId: item.id
          }
        },
        update: {
          quantity: { increment: 1 }
        },
        create: {
          userId: decoded.userId,
          itemId: item.id,
          quantity: 1
        }
      });
    }

    // Create case open record
    const caseOpen = await prisma.caseOpen.create({
      data: {
        userId: decoded.userId,
        caseId: caseData.id,
        items: JSON.stringify(droppedItems.map(item => item.id)),
        totalValue,
        currency: caseData.currency
      }
    });

    // Create transaction
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'CASE_OPEN',
        amount: -caseData.price,
        currency: caseData.currency,
        description: `Opened case: ${caseData.name}`
      }
    });

    // Add experience
    await prisma.user.update({
      where: { id: decoded.userId },
      data: { experience: { increment: 25 } }
    });

    res.json({
      success: true,
      drops: droppedItems,
      totalValue,
      caseOpenId: caseOpen.id
    });

  } catch (error) {
    console.error('Open case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Helper function to calculate drops based on drop rates
function calculateDrops(caseItems: any[]): any[] {
  const drops = [];
  const rand = Math.random() * 100;
  
  let cumulativeRate = 0;
  for (const caseItem of caseItems) {
    cumulativeRate += caseItem.dropRate;
    if (rand <= cumulativeRate) {
      drops.push(caseItem);
      break;
    }
  }
  
  // If no drop matched (shouldn't happen with proper rates), give first item
  if (drops.length === 0 && caseItems.length > 0) {
    drops.push(caseItems[0]);
  }
  
  return drops;
}

// Battle case opening (PvP)
router.post('/battle', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { caseId, opponentId } = req.body;
    
    // This is a simplified version - in production you'd need real-time battle logic
    const caseData = await prisma.case.findUnique({
      where: { id: caseId },
      include: {
        items: { include: { item: true } }
      }
    });

    if (!caseData || !caseData.battleMode) {
      return res.status(400).json({ error: 'Case does not support battle mode' });
    }

    // Deduct cost from both players
    await prisma.user.update({
      where: { id: decoded.userId },
      data: { balance: { decrement: caseData.price } }
    });

    await prisma.user.update({
      where: { id: opponentId },
      data: { balance: { decrement: caseData.price } }
    });

    // Open cases for both players
    const playerDrops = calculateDrops(caseData.items);
    const opponentDrops = calculateDrops(caseData.items);

    const playerValue = playerDrops.reduce((sum, drop) => sum + drop.item.basePrice, 0);
    const opponentValue = opponentDrops.reduce((sum, drop) => sum + drop.item.basePrice, 0);

    // Determine winner
    const playerWon = playerValue >= opponentValue;
    const winnerId = playerWon ? decoded.userId : opponentId;
    const loserId = playerWon ? opponentId : decoded.userId;

    // Give items to both players
    for (const drop of [...playerDrops, ...opponentDrops]) {
      const targetUserId = playerDrops.includes(drop) ? decoded.userId : opponentId;
      await prisma.inventoryItem.upsert({
        where: {
          userId_itemId: {
            userId: targetUserId,
            itemId: drop.item.id
          }
        },
        update: { quantity: { increment: 1 } },
        create: {
          userId: targetUserId,
          itemId: drop.item.id,
          quantity: 1
        }
      });
    }

    // Give bonus to winner
    const bonus = caseData.price * 0.1; // 10% bonus
    await prisma.user.update({
      where: { id: winnerId },
      data: { balance: { increment: bonus } }
    });

    // Create battle records
    const battleId = `battle_${Date.now()}`;
    
    await prisma.caseOpen.create({
      data: {
        userId: decoded.userId,
        caseId: caseData.id,
        items: JSON.stringify(playerDrops.map(d => d.item.id)),
        totalValue: playerValue,
        isBattle: true,
        battleId
      }
    });

    await prisma.caseOpen.create({
      data: {
        userId: opponentId,
        caseId: caseData.id,
        items: JSON.stringify(opponentDrops.map(d => d.item.id)),
        totalValue: opponentValue,
        isBattle: true,
        battleId
      }
    });

    // Create transactions
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: playerWon ? 'BATTLE_WIN' : 'BATTLE_LOSE',
        amount: playerWon ? bonus : -caseData.price,
        description: `Battle ${playerWon ? 'won' : 'lost'}`
      }
    });

    res.json({
      success: true,
      battleId,
      playerDrops: playerDrops.map(d => d.item),
      opponentDrops: opponentDrops.map(d => d.item),
      playerValue,
      opponentValue,
      winner: winnerId,
      bonus
    });

  } catch (error) {
    console.error('Battle case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;