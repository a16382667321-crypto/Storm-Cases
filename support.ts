import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get user's support tickets
router.get('/tickets', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const tickets = await prisma.supportTicket.findMany({
      where: { userId: decoded.userId },
      include: {
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
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json(tickets);

  } catch (error) {
    console.error('Get tickets error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create support ticket
router.post('/tickets', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { subject, message, category, priority } = req.body;
    
    const ticket = await prisma.supportTicket.create({
      data: {
        userId: decoded.userId,
        subject,
        message,
        category: category || 'GENERAL',
        priority: priority || 'MEDIUM'
      }
    });

    res.json({ success: true, ticket });

  } catch (error) {
    console.error('Create ticket error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Add response to ticket
router.post('/tickets/:id/respond', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { message } = req.body;
    
    const ticket = await prisma.supportTicket.findUnique({
      where: { id: req.params.id }
    });

    if (!ticket) {
      return res.status(404).json({ error: 'Ticket not found' });
    }

    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Only ticket owner or admins can respond
    if (ticket.userId !== decoded.userId && !user.isAdmin) {
      return res.status(403).json({ error: 'Not authorized' });
    }

    const response = await prisma.supportResponse.create({
      data: {
        ticketId: req.params.id,
        userId: decoded.userId,
        isAdmin: user.isAdmin,
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

    // Update ticket status if user responds
    if (!user.isAdmin) {
      await prisma.supportTicket.update({
        where: { id: req.params.id },
        data: { status: 'IN_PROGRESS' }
      });
    }

    res.json({ success: true, response });

  } catch (error) {
    console.error('Add response error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get specific ticket
router.get('/tickets/:id', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const ticket = await prisma.supportTicket.findUnique({
      where: { id: req.params.id },
      include: {
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
        },
        user: {
          select: {
            id: true,
            username: true
          }
        }
      }
    });

    if (!ticket) {
      return res.status(404).json({ error: 'Ticket not found' });
    }

    // Check authorization
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user || (ticket.userId !== decoded.userId && !user.isAdmin)) {
      return res.status(403).json({ error: 'Not authorized' });
    }

    res.json(ticket);

  } catch (error) {
    console.error('Get ticket error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Close ticket
router.put('/tickets/:id/close', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const ticket = await prisma.supportTicket.findUnique({
      where: { id: req.params.id }
    });

    if (!ticket) {
      return res.status(404).json({ error: 'Ticket not found' });
    }

    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user || (ticket.userId !== decoded.userId && !user.isAdmin)) {
      return res.status(403).json({ error: 'Not authorized' });
    }

    const updated = await prisma.supportTicket.update({
      where: { id: req.params.id },
      data: { status: 'CLOSED' }
    });

    res.json({ success: true, ticket: updated });

  } catch (error) {
    console.error('Close ticket error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;