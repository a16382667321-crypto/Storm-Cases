import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'your-super-secret-jwt-key-change-this';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

export interface JwtPayload {
  userId: string;
  telegramId: string;
}

export function generateAuthToken(userId: string): string {
  const payload: JwtPayload = {
    userId,
    telegramId: '' // Will be filled from user data
  };
  
  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

export function verifyAuthToken(token: string): JwtPayload {
  try {
    return jwt.verify(token, JWT_SECRET) as JwtPayload;
  } catch (error) {
    throw new Error('Invalid token');
  }
}

export function generateAdminToken(userId: string): string {
  const payload = {
    userId,
    isAdmin: true
  };
  
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '1h' });
}