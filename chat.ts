import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get chat history
router.get('/history', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = parseInt(req.query.offset as string) || 0;

    const messages = await prisma.chatMessage.findMany({
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            level: true,
            isAdmin: true,
            isModerator: true
          }
        }
      }
    });

    res.json(messages.reverse());

  } catch (error) {
    console.error('Get chat history error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Report a message
router.post('/report', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { messageId, reason } = req.body;
    
    // Create support ticket for report
    const message = await prisma.chatMessage.findUnique({
      where: { id: messageId },
      include: { user: true }
    });

    if (!message) {
      return res.status(404).json({ error: 'Message not found' });
    }

    await prisma.supportTicket.create({
      data: {
        userId: decoded.userId,
        subject: `Chat Report: ${message.user?.username}`,
        message: `Reported message: ${message.message}\nReason: ${reason}\nMessage ID: ${messageId}`,
        category: 'CHAT_REPORT',
        priority: 'MEDIUM'
      }
    });

    res.json({ success: true, message: 'Report submitted' });

  } catch (error) {
    console.error('Report message error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get online users
router.get('/online', async (req, res) => {
  try {
    // This would typically come from Socket.io connected clients
    // For now, return recent active users
    const recentUsers = await prisma.user.findMany({
      where: {
        isBanned: false,
        updatedAt: {
          gte: new Date(Date.now() - 15 * 60 * 1000) // Active in last 15 minutes
        }
      },
      select: {
        id: true,
        username: true,
        level: true,
        isAdmin: true,
        isModerator: true
      },
      take: 50
    });

    res.json(recentUsers);

  } catch (error) {
    console.error('Get online users error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add reaction to message
router.post('/:id/react', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { emoji } = req.body;
    
    const message = await prisma.chatMessage.findUnique({
      where: { id: req.params.id }
    });

    if (!message) {
      return res.status(404).json({ error: 'Message not found' });
    }

    // Parse existing reactions
    let reactions = message.reactions ? JSON.parse(message.reactions) : [];
    
    // Check if user already reacted
    const existingReaction = reactions.find((r: any) => r.userId === decoded.userId);
    
    if (existingReaction) {
      // Update existing reaction
      existingReaction.emoji = emoji;
    } else {
      // Add new reaction
      reactions.push({
        userId: decoded.userId,
        emoji,
        timestamp: new Date().toISOString()
      });
    }

    await prisma.chatMessage.update({
      where: { id: req.params.id },
      data: { reactions: JSON.stringify(reactions) }
    });

    res.json({ success: true, reactions });

  } catch (error) {
    console.error('Add reaction error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;