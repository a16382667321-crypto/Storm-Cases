import express from 'express';
import { verifyAuthToken, generateAdminToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Middleware to check admin access
const adminAuth = async (req: express.Request, res: express.Response, next: express.NextFunction) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const adminToken = req.headers['x-admin-token'] as string;
    
    if (!adminToken) {
      return res.status(401).json({ error: 'Admin token required' });
    }

    const decoded = verifyAuthToken(token);
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user || !user.isAdmin) {
      return res.status(403).json({ error: 'Not authorized as admin' });
    }

    req.admin = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Authentication failed' });
  }
};

// Extend Express Request type
declare global {
  namespace Express {
    interface Request {
      admin?: any;
    }
  }
};

// ==================== USERS MANAGEMENT ====================

// Get all users with search and pagination
router.get('/users', adminAuth, async (req, res) => {
  try {
    const { search, page = 1, limit = 50 } = req.query;
    const skip = (Number(page) - 1) * Number(limit);

    const where = search ? {
      OR: [
        { username: { contains: search as string, mode: 'insensitive' as any } },
        { telegramId: { contains: search as string } },
        { firstName: { contains: search as string, mode: 'insensitive' as any } }
      ]
    } : {};

    const [users, total] = await Promise.all([
      prisma.user.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          telegramId: true,
          username: true,
          firstName: true,
          lastName: true,
          isAdmin: true,
          isModerator: true,
          isMuted: true,
          isBanned: true,
          muteUntil: true,
          banReason: true,
          balance: true,
          premiumBalance: true,
          level: true,
          experience: true,
          reputation: true,
          createdAt: true,
          updatedAt: true
        }
      }),
      prisma.user.count({ where })
    ]);

    res.json({ users, total, page: Number(page), limit: Number(limit) });

  } catch (error) {
    console.error('Get users error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get specific user details
router.get('/users/:id', adminAuth, async (req, res) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.params.id },
      include: {
        inventory: { include: { item: true } },
        transactions: { take: 20, orderBy: { createdAt: 'desc' } },
        logs: { take: 20, orderBy: { createdAt: 'desc' } }
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user);

  } catch (error) {
    console.error('Get user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Mute user
router.put('/users/:id/mute', adminAuth, async (req, res) => {
  try {
    const { duration, reason } = req.body;
    const muteUntil = duration ? new Date(Date.now() + duration * 60 * 1000) : null;

    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: {
        isMuted: true,
        muteUntil,
        banReason: reason
      }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'MUTE',
        details: JSON.stringify({ duration, reason, adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Mute user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Unmute user
router.put('/users/:id/unmute', adminAuth, async (req, res) => {
  try {
    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: {
        isMuted: false,
        muteUntil: null
      }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'UNMUTE',
        details: JSON.stringify({ adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Unmute user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Ban user
router.put('/users/:id/ban', adminAuth, async (req, res) => {
  try {
    const { reason } = req.body;

    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: {
        isBanned: true,
        banReason: reason
      }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'BAN',
        details: JSON.stringify({ reason, adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Ban user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Unban user
router.put('/users/:id/unban', adminAuth, async (req, res) => {
  try {
    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: {
        isBanned: false,
        banReason: null
      }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'UNBAN',
        details: JSON.stringify({ adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Unban user error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Give balance to user
router.put('/users/:id/balance', adminAuth, async (req, res) => {
  try {
    const { amount, currency, reason } = req.body;

    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: {
        [currency === 'PREMIUM_COINS' ? 'premiumBalance' : 'balance']: {
          increment: amount
        }
      }
    });

    // Create transaction
    await prisma.transaction.create({
      data: {
        userId: req.params.id,
        type: 'ADMIN_GIVE',
        amount,
        currency: currency || 'STORM_COINS',
        description: reason || 'Admin balance adjustment'
      }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'BALANCE_ADJUSTMENT',
        details: JSON.stringify({ amount, currency, reason, adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Give balance error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Make user moderator
router.put('/users/:id/moderator', adminAuth, async (req, res) => {
  try {
    const { isModerator } = req.body;

    const user = await prisma.user.update({
      where: { id: req.params.id },
      data: { isModerator }
    });

    // Log the action
    await prisma.activityLog.create({
      data: {
        userId: req.params.id,
        action: 'MODERATOR_CHANGE',
        details: JSON.stringify({ isModerator, adminId: req.admin.id })
      }
    });

    res.json({ success: true, user });

  } catch (error) {
    console.error('Set moderator error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== ACTIVITY LOGS ====================

// Get user activity logs
router.get('/users/:id/logs', adminAuth, async (req, res) => {
  try {
    const { page = 1, limit = 50 } = req.query;
    const skip = (Number(page) - 1) * Number(limit);

    const [logs, total] = await Promise.all([
      prisma.activityLog.findMany({
        where: { userId: req.params.id },
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' }
      }),
      prisma.activityLog.count({ where: { userId: req.params.id } })
    ]);

    res.json({ logs, total, page: Number(page), limit: Number(limit) });

  } catch (error) {
    console.error('Get logs error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all activity logs
router.get('/logs', adminAuth, async (req, res) => {
  try {
    const { page = 1, limit = 50, action, userId } = req.query;
    const skip = (Number(page) - 1) * Number(limit);

    const where: any = {};
    if (action) where.action = action;
    if (userId) where.userId = userId;

    const [logs, total] = await Promise.all([
      prisma.activityLog.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' },
        include: {
          user: {
            select: {
              id: true,
              username: true,
              telegramId: true
            }
          }
        }
      }),
      prisma.activityLog.count({ where })
    ]);

    res.json({ logs, total, page: Number(page), limit: Number(limit) });

  } catch (error) {
    console.error('Get all logs error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== SUPPORT TICKETS ====================

// Get all support tickets
router.get('/support/tickets', adminAuth, async (req, res) => {
  try {
    const { status, priority, page = 1, limit = 50 } = req.query;
    const skip = (Number(page) - 1) * Number(limit);

    const where: any = {};
    if (status) where.status = status;
    if (priority) where.priority = priority;

    const [tickets, total] = await Promise.all([
      prisma.supportTicket.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { createdAt: 'desc' },
        include: {
          user: {
            select: {
              id: true,
              username: true,
              telegramId: true
            }
          },
          responses: {
            include: {
              user: {
                select: {
                  id: true,
                  username: true,
                  isAdmin: true
                }
              }
            },
            orderBy: { createdAt: 'asc' }
          }
        }
      }),
      prisma.supportTicket.count({ where })
    ]);

    res.json({ tickets, total, page: Number(page), limit: Number(limit) });

  } catch (error) {
    console.error('Get support tickets error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Respond to support ticket
router.post('/support/tickets/:id/respond', adminAuth, async (req, res) => {
  try {
    const { message } = req.body;

    const response = await prisma.supportResponse.create({
      data: {
        ticketId: req.params.id,
        userId: req.admin.id,
        isAdmin: true,
        message
      },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            isAdmin: true
          }
        }
      }
    });

    // Update ticket status
    await prisma.supportTicket.update({
      where: { id: req.params.id },
      data: { status: 'IN_PROGRESS' }
    });

    res.json({ success: true, response });

  } catch (error) {
    console.error('Respond to ticket error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update ticket status
router.put('/support/tickets/:id/status', adminAuth, async (req, res) => {
  try {
    const { status } = req.body;

    const ticket = await prisma.supportTicket.update({
      where: { id: req.params.id },
      data: { status }
    });

    res.json({ success: true, ticket });

  } catch (error) {
    console.error('Update ticket status error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== ECONOMY ====================

// Get currency rates
router.get('/economy/rates', adminAuth, async (req, res) => {
  try {
    const rates = await prisma.currencyRate.findMany();
    res.json(rates);

  } catch (error) {
    console.error('Get rates error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update currency rate
router.put('/economy/rates', adminAuth, async (req, res) => {
  try {
    const { fromCurrency, toCurrency, rate } = req.body;

    const currencyRate = await prisma.currencyRate.upsert({
      where: {
        fromCurrency_toCurrency: {
          fromCurrency,
          toCurrency
        }
      },
      update: { rate },
      create: { fromCurrency, toCurrency, rate }
    });

    res.json({ success: true, currencyRate });

  } catch (error) {
    console.error('Update rate error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create promo code
router.post('/economy/promocodes', adminAuth, async (req, res) => {
  try {
    const { code, reward, rewardType, maxUses, expiresAt } = req.body;

    const promoCode = await prisma.promoCode.create({
      data: {
        code,
        reward,
        rewardType,
        maxUses,
        expiresAt: expiresAt ? new Date(expiresAt) : null,
        createdBy: req.admin.id
      }
    });

    res.json({ success: true, promoCode });

  } catch (error) {
    console.error('Create promo code error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all promo codes
router.get('/economy/promocodes', adminAuth, async (req, res) => {
  try {
    const promoCodes = await prisma.promoCode.findMany({
      orderBy: { createdAt: 'desc' }
    });

    res.json(promoCodes);

  } catch (error) {
    console.error('Get promo codes error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Redeem promo code (public endpoint)
router.post('/economy/promocodes/redeem', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { code } = req.body;

    const promoCode = await prisma.promoCode.findUnique({
      where: { code }
    });

    if (!promoCode || !promoCode.isActive) {
      return res.status(404).json({ error: 'Invalid promo code' });
    }

    if (promoCode.maxUses && promoCode.usedCount >= promoCode.maxUses) {
      return res.status(400).json({ error: 'Promo code expired (max uses reached)' });
    }

    if (promoCode.expiresAt && new Date() > promoCode.expiresAt) {
      return res.status(400).json({ error: 'Promo code expired' });
    }

    // Give reward
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    let rewardData: any = {};
    
    switch (promoCode.rewardType) {
      case 'BALANCE':
        await prisma.user.update({
          where: { id: decoded.userId },
          data: { balance: { increment: promoCode.reward } }
        });
        rewardData = { balance: user.balance + promoCode.reward };
        break;
      case 'PREMIUM_BALANCE':
        await prisma.user.update({
          where: { id: decoded.userId },
          data: { premiumBalance: { increment: promoCode.reward } }
        });
        rewardData = { premiumBalance: user.premiumBalance + promoCode.reward };
        break;
      case 'XP':
        await prisma.user.update({
          where: { id: decoded.userId },
          data: { experience: { increment: promoCode.reward } }
        });
        rewardData = { experience: user.experience + promoCode.reward };
        break;
    }

    // Update promo code usage
    await prisma.promoCode.update({
      where: { id: promoCode.id },
      data: { usedCount: { increment: 1 } }
    });

    // Create transaction
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'PROMO_CODE',
        amount: promoCode.reward,
        description: `Redeemed promo code: ${code}`
      }
    });

    res.json({ success: true, reward: rewardData });

  } catch (error) {
    console.error('Redeem promo code error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== CONTENT MANAGEMENT ====================

// Create case
router.post('/content/cases', adminAuth, async (req, res) => {
  try {
    const caseData = req.body;

    const newCase = await prisma.case.create({
      data: caseData
    });

    res.json({ success: true, case: newCase });

  } catch (error) {
    console.error('Create case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update case
router.put('/content/cases/:id', adminAuth, async (req, res) => {
  try {
    const updatedCase = await prisma.case.update({
      where: { id: req.params.id },
      data: req.body
    });

    res.json({ success: true, case: updatedCase });

  } catch (error) {
    console.error('Update case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete case
router.delete('/content/cases/:id', adminAuth, async (req, res) => {
  try {
    await prisma.case.delete({
      where: { id: req.params.id }
    });

    res.json({ success: true, message: 'Case deleted' });

  } catch (error) {
    console.error('Delete case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create item
router.post('/content/items', adminAuth, async (req, res) => {
  try {
    const itemData = req.body;

    const newItem = await prisma.item.create({
      data: itemData
    });

    res.json({ success: true, item: newItem });

  } catch (error) {
    console.error('Create item error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update item
router.put('/content/items/:id', adminAuth, async (req, res) => {
  try {
    const updatedItem = await prisma.item.update({
      where: { id: req.params.id },
      data: req.body
    });

    res.json({ success: true, item: updatedItem });

  } catch (error) {
    console.error('Update item error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add item to case
router.post('/content/cases/:caseId/items/:itemId', adminAuth, async (req, res) => {
  try {
    const { dropRate, isGuaranteed } = req.body;

    const caseItem = await prisma.caseItem.create({
      data: {
        caseId: req.params.caseId,
        itemId: req.params.itemId,
        dropRate,
        isGuaranteed
      }
    });

    res.json({ success: true, caseItem });

  } catch (error) {
    console.error('Add item to case error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== ANALYTICS ====================

// Get general statistics
router.get('/analytics/stats', adminAuth, async (req, res) => {
  try {
    const [
      totalUsers,
      activeUsers,
      totalCasesOpened,
      totalTransactions,
      totalVolume,
      onlineUsers
    ] = await Promise.all([
      prisma.user.count(),
      prisma.user.count({
        where: {
          updatedAt: {
            gte: new Date(Date.now() - 24 * 60 * 60 * 1000)
          }
        }
      }),
      prisma.caseOpen.count(),
      prisma.transaction.count(),
      prisma.transaction.aggregate({
        _sum: { amount: true }
      }),
      prisma.user.count({
        where: {
          updatedAt: {
            gte: new Date(Date.now() - 15 * 60 * 1000)
          }
        }
      })
    ]);

    res.json({
      totalUsers,
      activeUsers,
      totalCasesOpened,
      totalTransactions,
      totalVolume: totalVolume._sum.amount || 0,
      onlineUsers
    });

  } catch (error) {
    console.error('Get analytics error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get revenue statistics
router.get('/analytics/revenue', adminAuth, async (req, res) => {
  try {
    const { period = '7d' } = req.query;
    
    const startDate = new Date();
    switch (period) {
      case '1d':
        startDate.setDate(startDate.getDate() - 1);
        break;
      case '7d':
        startDate.setDate(startDate.getDate() - 7);
        break;
      case '30d':
        startDate.setDate(startDate.getDate() - 30);
        break;
      case '90d':
        startDate.setDate(startDate.getDate() - 90);
        break;
    }

    const transactions = await prisma.transaction.findMany({
      where: {
        createdAt: { gte: startDate },
        type: { in: ['CASE_OPEN', 'ITEM_PURCHASE', 'ITEM_SALE'] }
      },
      orderBy: { createdAt: 'asc' }
    });

    // Group by date
    const revenueByDate = transactions.reduce((acc: any, transaction) => {
      const date = transaction.createdAt.toISOString().split('T')[0];
      if (!acc[date]) {
        acc[date] = { date, revenue: 0, count: 0 };
      }
      acc[date].revenue += Math.abs(transaction.amount);
      acc[date].count += 1;
      return acc;
    }, {});

    res.json(Object.values(revenueByDate));

  } catch (error) {
    console.error('Get revenue error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get popular items
router.get('/analytics/popular-items', adminAuth, async (req, res) => {
  try {
    const popularItems = await prisma.inventoryItem.groupBy({
      by: ['itemId'],
      _count: { itemId: true },
      orderBy: { _count: { itemId: 'desc' } },
      take: 10
    });

    const itemsWithDetails = await Promise.all(
      popularItems.map(async (item) => {
        const details = await prisma.item.findUnique({
          where: { id: item.itemId }
        });
        return {
          ...details,
          count: item._count.itemId
        };
      })
    );

    res.json(itemsWithDetails);

  } catch (error) {
    console.error('Get popular items error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ==================== MODERATION ====================

// Get all chat reports
router.get('/moderation/reports', adminAuth, async (req, res) => {
  try {
    const reports = await prisma.supportTicket.findMany({
      where: { category: 'CHAT_REPORT' },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            telegramId: true
          }
        },
        responses: true
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json(reports);

  } catch (error) {
    console.error('Get reports error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get flagged messages
router.get('/moderation/flagged', adminAuth, async (req, res) => {
  try {
    // This would integrate with content moderation system
    // For now, return recent messages for review
    const messages = await prisma.chatMessage.findMany({
      take: 100,
      orderBy: { createdAt: 'desc' },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            isMuted: true,
            isBanned: true
          }
        }
      }
    });

    res.json(messages);

  } catch (error) {
    console.error('Get flagged messages error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete chat message
router.delete('/moderation/messages/:id', adminAuth, async (req, res) => {
  try {
    await prisma.chatMessage.delete({
      where: { id: req.params.id }
    });

    res.json({ success: true, message: 'Message deleted' });

  } catch (error) {
    console.error('Delete message error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;