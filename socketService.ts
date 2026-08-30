import { Server as SocketIOServer } from 'socket.io';
import jwt from 'jsonwebtoken';
import prisma from '../config/database';

let io: SocketIOServer;

export function initializeSocket(socketIOServer: SocketIOServer) {
  io = socketIOServer;

  io.on('connection', async (socket) => {
    console.log('User connected:', socket.id);

    // Authentication
    const token = socket.handshake.auth.token;
    if (!token) {
      socket.disconnect();
      return;
    }

    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET || 'default-secret') as any;
      const user = await prisma.user.findUnique({
        where: { id: decoded.userId }
      });

      if (!user || user.isBanned) {
        socket.disconnect();
        return;
      }

      socket.data.userId = user.id;
      socket.data.username = user.username;

      // Join user's personal room
      socket.join(`user:${user.id}`);

      // Join global chat
      socket.join('global-chat');

      // Send online status
      io.to('global-chat').emit('user_joined', {
        userId: user.id,
        username: user.username,
        online: true
      });

    } catch (error) {
      console.error('Socket authentication error:', error);
      socket.disconnect();
      return;
    }

    // Chat message handling
    socket.on('send_message', async (data) => {
      try {
        const { message, replyTo } = data;
        const userId = socket.data.userId;
        const username = socket.data.username;

        if (!message || message.trim().length === 0) return;
        if (message.length > 500) {
          socket.emit('error', { message: 'Message too long' });
          return;
        }

        // Check if user is muted
        const user = await prisma.user.findUnique({
          where: { id: userId }
        });

        if (user?.isMuted && user.muteUntil && user.muteUntil > new Date()) {
          socket.emit('error', { message: 'You are muted' });
          return;
        }

        // Save message to database
        const chatMessage = await prisma.chatMessage.create({
          data: {
            userId,
            username,
            message: message.trim(),
            replyTo
          }
        });

        // Broadcast to global chat
        io.to('global-chat').emit('new_message', {
          id: chatMessage.id,
          userId: chatMessage.userId,
          username: chatMessage.username,
          message: chatMessage.message,
          replyTo: chatMessage.replyTo,
          createdAt: chatMessage.createdAt
        });

      } catch (error) {
        console.error('Error sending message:', error);
        socket.emit('error', { message: 'Failed to send message' });
      }
    });

    // Join admin chat
    socket.on('join_admin_chat', async () => {
      try {
        const userId = socket.data.userId;
        const user = await prisma.user.findUnique({
          where: { id: userId }
        });

        if (!user?.isAdmin) {
          socket.emit('error', { message: 'Not authorized' });
          return;
        }

        socket.join('admin-chat');
        socket.emit('admin_chat_joined', { success: true });

      } catch (error) {
        console.error('Error joining admin chat:', error);
      }
    });

    // Admin chat message
    socket.on('admin_message', async (data) => {
      try {
        const userId = socket.data.userId;
        const user = await prisma.user.findUnique({
          where: { id: userId }
        });

        if (!user?.isAdmin) {
          socket.emit('error', { message: 'Not authorized' });
          return;
        }

        io.to('admin-chat').emit('admin_chat_message', {
          userId,
          username: user.username,
          message: data.message,
          timestamp: new Date()
        });

      } catch (error) {
        console.error('Error in admin chat:', error);
      }
    });

    // Typing indicator
    socket.on('typing', () => {
      socket.to('global-chat').emit('user_typing', {
        userId: socket.data.userId,
        username: socket.data.username
      });
    });

    // Disconnect handling
    socket.on('disconnect', () => {
      console.log('User disconnected:', socket.id);
      io.to('global-chat').emit('user_left', {
        userId: socket.data.userId,
        username: socket.data.username
      });
    });
  });

  console.log('✅ Socket.io initialized');
}

export function getIO(): SocketIOServer {
  if (!io) {
    throw new Error('Socket.io not initialized');
  }
  return io;
}

// Helper function to send notification to specific user
export function sendNotificationToUser(userId: string, notification: any) {
  if (io) {
    io.to(`user:${userId}`).emit('notification', notification);
  }
}

// Helper function to broadcast to global chat
export function broadcastToGlobalChat(event: string, data: any) {
  if (io) {
    io.to('global-chat').emit(event, data);
  }
}