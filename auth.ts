import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Verify token and get user data
router.get('/verify', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = verifyAuthToken(token);
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId },
      include: {
        inventory: {
          include: { item: true }
        }
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    if (user.isBanned) {
      return res.status(403).json({ error: 'User is banned', reason: user.banReason });
    }

    res.json({
      user: {
        id: user.id,
        telegramId: user.telegramId,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        balance: user.balance,
        premiumBalance: user.premiumBalance,
        level: user.level,
        experience: user.experience,
        reputation: user.reputation,
        isAdmin: user.isAdmin,
        isModerator: user.isModerator,
        isPremium: user.isPremium,
        referralCode: user.referralCode,
        dailyStreak: user.dailyStreak,
        lastDailyClaim: user.lastDailyClaim
      },
      inventory: user.inventory
    });

  } catch (error) {
    console.error('Auth verification error:', error);
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Admin login
router.post('/admin-login', async (req, res) => {
  try {
    const { password } = req.body;
    const adminPassword = process.env.ADMIN_PASSWORD;

    if (password !== adminPassword) {
      return res.status(401).json({ error: 'Invalid password' });
    }

    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = verifyAuthToken(token);
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user || !user.isAdmin) {
      return res.status(403).json({ error: 'Not authorized as admin' });
    }

    const adminToken = require('../utils/jwt').generateAdminToken(user.id);
    
    res.json({ 
      success: true, 
      adminToken,
      user: {
        id: user.id,
        username: user.username,
        isAdmin: user.isAdmin
      }
    });

  } catch (error) {
    console.error('Admin login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;