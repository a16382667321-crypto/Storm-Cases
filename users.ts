import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get user profile
router.get('/profile', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
      include: {
        inventory: { include: { item: true } },
        achievements: { include: { achievement: true } }
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user);

  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update user profile
router.put('/profile', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const { username } = req.body;
    
    const user = await prisma.user.update({
      where: { id: decoded.userId },
      data: { username }
    });

    res.json(user);

  } catch (error) {
    console.error('Update profile error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Claim daily reward
router.post('/daily-reward', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const now = new Date();
    const lastClaim = user.lastDailyClaim ? new Date(user.lastDailyClaim) : null;
    
    // Check if can claim (24 hours since last claim)
    if (lastClaim && (now.getTime() - lastClaim.getTime()) < 24 * 60 * 60 * 1000) {
      return res.status(400).json({ error: 'Daily reward already claimed' });
    }

    // Calculate reward based on streak
    const streak = (lastClaim && (now.getTime() - lastClaim.getTime()) < 48 * 60 * 60 * 1000) 
      ? user.dailyStreak + 1 
      : 1;
    
    const baseReward = 100;
    const streakBonus = Math.min(streak * 10, 100); // Max 100 bonus
    const totalReward = baseReward + streakBonus;

    // Update user
    const updatedUser = await prisma.user.update({
      where: { id: decoded.userId },
      data: {
        balance: { increment: totalReward },
        dailyStreak: streak,
        lastDailyClaim: now,
        experience: { increment: 10 }
      }
    });

    // Create transaction record
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'DAILY_REWARD',
        amount: totalReward,
        description: `Daily reward (streak: ${streak})`
      }
    });

    res.json({ 
      success: true, 
      reward: totalReward, 
      streak,
      newBalance: updatedUser.balance 
    });

  } catch (error) {
    console.error('Daily reward error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Refer a friend
router.post('/refer', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { referralCode } = req.body;
    
    const referrer = await prisma.user.findFirst({
      where: { referralCode }
    });

    if (!referrer) {
      return res.status(404).json({ error: 'Invalid referral code' });
    }

    if (referrer.id === decoded.userId) {
      return res.status(400).json({ error: 'Cannot refer yourself' });
    }

    // Update user with referrer
    const user = await prisma.user.update({
      where: { id: decoded.userId },
      data: { referredBy: referrer.id }
    });

    // Give rewards
    await prisma.user.update({
      where: { id: referrer.id },
      data: { 
        balance: { increment: 500 },
        experience: { increment: 50 }
      }
    });

    await prisma.user.update({
      where: { id: decoded.userId },
      data: { 
        balance: { increment: 200 },
        experience: { increment: 20 }
      }
    });

    // Create transaction records
    await prisma.transaction.create({
      data: {
        userId: referrer.id,
        type: 'REFERRAL',
        amount: 500,
        description: 'Referral bonus'
      }
    });

    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'REFERRAL',
        amount: 200,
        description: 'Referral reward'
      }
    });

    res.json({ success: true, message: 'Referral code applied successfully' });

  } catch (error) {
    console.error('Referral error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;