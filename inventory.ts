import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get user inventory
router.get('/', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const inventory = await prisma.inventoryItem.findMany({
      where: { userId: decoded.userId },
      include: { item: true },
      orderBy: { obtainedAt: 'desc' }
    });

    res.json(inventory);

  } catch (error) {
    console.error('Get inventory error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Craft items
router.post('/craft', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { itemId } = req.body;
    
    const targetItem = await prisma.item.findUnique({
      where: { id: itemId }
    });

    if (!targetItem || !targetItem.isCraftable) {
      return res.status(400).json({ error: 'Item is not craftable' });
    }

    const requiredItems = targetItem.craftFrom; // Array of item IDs
    const requiredAmount = targetItem.craftAmount;

    // Check if user has required items
    const userInventory = await prisma.inventoryItem.findMany({
      where: { 
        userId: decoded.userId,
        itemId: { in: requiredItems }
      }
    });

    const hasEnoughItems = requiredItems.every(reqItemId => {
      const invItem = userInventory.find(inv => inv.itemId === reqItemId);
      return invItem && invItem.quantity >= requiredAmount;
    });

    if (!hasEnoughItems) {
      return res.status(400).json({ error: 'Insufficient materials' });
    }

    // Deduct required items
    for (const reqItemId of requiredItems) {
      const invItem = userInventory.find(inv => inv.itemId === reqItemId);
      if (invItem) {
        await prisma.inventoryItem.update({
          where: { id: invItem.id },
          data: { quantity: { decrement: requiredAmount } }
        });
      }
    }

    // Add crafted item to inventory
    await prisma.inventoryItem.upsert({
      where: {
        userId_itemId: {
          userId: decoded.userId,
          itemId: targetItem.id
        }
      },
      update: { quantity: { increment: 1 } },
      create: {
        userId: decoded.userId,
        itemId: targetItem.id,
        quantity: 1
      }
    });

    // Create transaction
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'CRAFT',
        amount: 0,
        description: `Crafted ${targetItem.name}`
      }
    });

    // Add experience
    await prisma.user.update({
      where: { id: decoded.userId },
      data: { experience: { increment: 15 } }
    });

    res.json({ 
      success: true, 
      craftedItem: targetItem 
    });

  } catch (error) {
    console.error('Craft item error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Upgrade item
router.post('/upgrade', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { fromItemId } = req.body;
    
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const inventoryItem = await prisma.inventoryItem.findFirst({
      where: { 
        id: fromItemId,
        userId: decoded.userId 
      },
      include: { item: true }
    });

    if (!inventoryItem) {
      return res.status(404).json({ error: 'Item not found in inventory' });
    }

    // Find upgrade path
    const upgrade = await prisma.itemUpgrade.findFirst({
      where: { fromItemId: inventoryItem.itemId },
      include: {
        fromItem: true,
        toItem: true
      }
    });

    if (!upgrade) {
      return res.status(400).json({ error: 'No upgrade available for this item' });
    }

    // Check balance
    const userBalance = upgrade.currency === 'STORM_COINS' ? user.balance : user.premiumBalance;
    if (userBalance < upgrade.cost) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }

    // Deduct cost
    await prisma.user.update({
      where: { id: decoded.userId },
      data: {
        [upgrade.currency === 'STORM_COINS' ? 'balance' : 'premiumBalance']: {
          decrement: upgrade.cost
        }
      }
    });

    // Roll for success
    const success = Math.random() * 100 < upgrade.successRate;

    if (success) {
      // Remove old item
      await prisma.inventoryItem.update({
        where: { id: inventoryItem.id },
        data: { quantity: { decrement: 1 } }
      });

      // Add new item
      await prisma.inventoryItem.upsert({
        where: {
          userId_itemId: {
            userId: decoded.userId,
            itemId: upgrade.toItemId
          }
        },
        update: { quantity: { increment: 1 } },
        create: {
          userId: decoded.userId,
          itemId: upgrade.toItemId,
          quantity: 1
        }
      });

      // Create transaction
      await prisma.transaction.create({
        data: {
          userId: decoded.userId,
          type: 'UPGRADE',
          amount: -upgrade.cost,
          currency: upgrade.currency,
          description: `Upgraded ${upgrade.fromItem.name} to ${upgrade.toItem.name}`
        }
      });

      res.json({ 
        success: true, 
        upgraded: true,
        newItem: upgrade.toItem 
      });
    } else {
      // Failed upgrade - just deduct cost
      await prisma.transaction.create({
        data: {
          userId: decoded.userId,
          type: 'UPGRADE',
          amount: -upgrade.cost,
          currency: upgrade.currency,
          description: `Failed upgrade attempt for ${upgrade.fromItem.name}`
        }
      });

      res.json({ 
        success: true, 
        upgraded: false,
        message: 'Upgrade failed' 
      });
    }

  } catch (error) {
    console.error('Upgrade item error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Toggle favorite
router.put('/:id/favorite', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const inventoryItem = await prisma.inventoryItem.findFirst({
      where: { 
        id: req.params.id,
        userId: decoded.userId 
      }
    });

    if (!inventoryItem) {
      return res.status(404).json({ error: 'Item not found' });
    }

    const updated = await prisma.inventoryItem.update({
      where: { id: req.params.id },
      data: { isFavorite: !inventoryItem.isFavorite }
    });

    res.json(updated);

  } catch (error) {
    console.error('Toggle favorite error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;