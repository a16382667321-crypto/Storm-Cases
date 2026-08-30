import express from 'express';
import { verifyAuthToken } from '../utils/jwt';
import prisma from '../config/database';

const router = express.Router();

// Get all market listings
router.get('/listings', async (req, res) => {
  try {
    const listings = await prisma.marketListing.findMany({
      where: { isActive: true },
      include: {
        seller: { select: { id: true, username: true } },
        item: true
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json(listings);

  } catch (error) {
    console.error('Get listings error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create market listing
router.post('/list', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { itemId, price, currency, isAuction, auctionEnd } = req.body;
    
    const inventoryItem = await prisma.inventoryItem.findFirst({
      where: { 
        id: itemId,
        userId: decoded.userId 
      },
      include: { item: true }
    });

    if (!inventoryItem) {
      return res.status(404).json({ error: 'Item not found in inventory' });
    }

    if (!inventoryItem.isTradable) {
      return res.status(400).json({ error: 'Item is not tradable' });
    }

    if (inventoryItem.quantity < 1) {
      return res.status(400).json({ error: 'Insufficient quantity' });
    }

    // Create listing
    const listing = await prisma.marketListing.create({
      data: {
        sellerId: decoded.userId,
        itemId: inventoryItem.itemId,
        price,
        currency,
        isAuction: isAuction || false,
        auctionEnd: isAuction ? new Date(auctionEnd) : null
      },
      include: {
        seller: { select: { id: true, username: true } },
        item: true
      }
    });

    // Remove item from inventory (will be returned if listing cancelled)
    await prisma.inventoryItem.update({
      where: { id: inventoryItem.id },
      data: { quantity: { decrement: 1 } }
    });

    res.json({ success: true, listing });

  } catch (error) {
    console.error('Create listing error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Buy item
router.post('/buy/:id', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const listing = await prisma.marketListing.findUnique({
      where: { id: req.params.id },
      include: {
        seller: true,
        item: true
      }
    });

    if (!listing || !listing.isActive) {
      return res.status(404).json({ error: 'Listing not found or not active' });
    }

    if (listing.sellerId === decoded.userId) {
      return res.status(400).json({ error: 'Cannot buy your own item' });
    }

    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Check balance
    const userBalance = listing.currency === 'STORM_COINS' ? user.balance : user.premiumBalance;
    if (userBalance < listing.price) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }

    // Deduct from buyer
    await prisma.user.update({
      where: { id: decoded.userId },
      data: {
        [listing.currency === 'STORM_COINS' ? 'balance' : 'premiumBalance']: {
          decrement: listing.price
        }
      }
    });

    // Add to seller (minus 5% fee)
    const fee = listing.price * 0.05;
    const sellerAmount = listing.price - fee;

    await prisma.user.update({
      where: { id: listing.sellerId },
      data: {
        [listing.currency === 'STORM_COINS' ? 'balance' : 'premiumBalance']: {
          increment: sellerAmount
        }
      }
    });

    // Add item to buyer inventory
    await prisma.inventoryItem.upsert({
      where: {
        userId_itemId: {
          userId: decoded.userId,
          itemId: listing.itemId
        }
      },
      update: { quantity: { increment: 1 } },
      create: {
        userId: decoded.userId,
        itemId: listing.itemId,
        quantity: 1
      }
    });

    // Update listing
    await prisma.marketListing.update({
      where: { id: req.params.id },
      data: {
        isActive: false,
        buyerId: decoded.userId,
        soldAt: new Date()
      }
    });

    // Create transactions
    await prisma.transaction.create({
      data: {
        userId: decoded.userId,
        type: 'ITEM_PURCHASE',
        amount: -listing.price,
        currency: listing.currency,
        description: `Purchased ${listing.item.name}`
      }
    });

    await prisma.transaction.create({
      data: {
        userId: listing.sellerId,
        type: 'ITEM_SALE',
        amount: sellerAmount,
        currency: listing.currency,
        description: `Sold ${listing.item.name}`
      }
    });

    await prisma.transaction.create({
      data: {
        userId: listing.sellerId,
        type: 'MARKET_FEE',
        amount: -fee,
        currency: listing.currency,
        description: 'Market fee'
      }
    });

    res.json({ success: true, message: 'Item purchased successfully' });

  } catch (error) {
    console.error('Buy item error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Cancel listing
router.delete('/listings/:id', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    
    const listing = await prisma.marketListing.findUnique({
      where: { id: req.params.id }
    });

    if (!listing) {
      return res.status(404).json({ error: 'Listing not found' });
    }

    if (listing.sellerId !== decoded.userId) {
      return res.status(403).json({ error: 'Not authorized to cancel this listing' });
    }

    if (!listing.isActive) {
      return res.status(400).json({ error: 'Listing already sold or cancelled' });
    }

    // Return item to seller
    await prisma.inventoryItem.upsert({
      where: {
        userId_itemId: {
          userId: decoded.userId,
          itemId: listing.itemId
        }
      },
      update: { quantity: { increment: 1 } },
      create: {
        userId: decoded.userId,
        itemId: listing.itemId,
        quantity: 1
      }
    });

    // Cancel listing
    await prisma.marketListing.update({
      where: { id: req.params.id },
      data: { isActive: false }
    });

    res.json({ success: true, message: 'Listing cancelled' });

  } catch (error) {
    console.error('Cancel listing error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Place bid on auction
router.post('/auctions/:id/bid', async (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const decoded = verifyAuthToken(token);
    const { amount } = req.body;
    
    const listing = await prisma.marketListing.findUnique({
      where: { id: req.params.id }
    });

    if (!listing || !listing.isActive || !listing.isAuction) {
      return res.status(404).json({ error: 'Auction not found or not active' });
    }

    if (listing.sellerId === decoded.userId) {
      return res.status(400).json({ error: 'Cannot bid on your own auction' });
    }

    if (listing.auctionEnd && new Date() > listing.auctionEnd) {
      return res.status(400).json({ error: 'Auction has ended' });
    }

    if (listing.currentBid && amount <= listing.currentBid) {
      return res.status(400).json({ error: 'Bid must be higher than current bid' });
    }

    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Check balance
    if (user.balance < amount) {
      return res.status(400).json({ error: 'Insufficient balance' });
    }

    // Update listing
    await prisma.marketListing.update({
      where: { id: req.params.id },
      data: { currentBid: amount }
    });

    res.json({ success: true, currentBid: amount });

  } catch (error) {
    console.error('Place bid error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;