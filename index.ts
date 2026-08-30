import express from 'express';
import authRoutes from './auth';
import userRoutes from './users';
import caseRoutes from './cases';
import inventoryRoutes from './inventory';
import marketRoutes from './market';
import chatRoutes from './chat';
import supportRoutes from './support';
import adminRoutes from './admin';

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/users', userRoutes);
router.use('/cases', caseRoutes);
router.use('/inventory', inventoryRoutes);
router.use('/market', marketRoutes);
router.use('/chat', chatRoutes);
router.use('/support', supportRoutes);
router.use('/admin', adminRoutes);

export default router;