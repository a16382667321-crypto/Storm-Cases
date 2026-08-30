import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting seed...');

  // Create admin user
  const adminPassword = await bcrypt.hash('admin123', 10);
  const admin = await prisma.user.upsert({
    where: { telegramId: 'admin_telegram_id' },
    update: {},
    create: {
      telegramId: 'admin_telegram_id',
      username: 'admin',
      firstName: 'Admin',
      lastName: 'User',
      isAdmin: true,
      isModerator: true,
      balance: 1000000,
      premiumBalance: 100000,
      level: 100,
      experience: 100000,
      referralCode: 'ADMIN000'
    }
  });
  console.log('✅ Admin user created');

  // Create sample cases
  const commonCase = await prisma.case.upsert({
    where: { id: 'common-case-1' },
    update: {},
    create: {
      id: 'common-case-1',
      name: 'Common Case',
      nameRu: 'Обычный кейс',
      description: 'Contains common items',
      descriptionRu: 'Содержит обычные предметы',
      rarity: 'COMMON',
      price: 100,
      currency: 'STORM_COINS',
      isActive: true
    }
  });

  const rareCase = await prisma.case.upsert({
    where: { id: 'rare-case-1' },
    update: {},
    create: {
      id: 'rare-case-1',
      name: 'Rare Case',
      nameRu: 'Редкий кейс',
      description: 'Contains rare and epic items',
      descriptionRu: 'Содержит редкие и эпические предметы',
      rarity: 'RARE',
      price: 500,
      currency: 'STORM_COINS',
      isActive: true
    }
  });

  const legendaryCase = await prisma.case.upsert({
    where: { id: 'legendary-case-1' },
    update: {},
    create: {
      id: 'legendary-case-1',
      name: 'Legendary Case',
      nameRu: 'Легендарный кейс',
      description: 'Contains legendary and mythical items',
      descriptionRu: 'Содержит легендарные и мифические предметы',
      rarity: 'LEGENDARY',
      price: 2000,
      currency: 'STORM_COINS',
      isActive: true
    }
  });

  console.log('✅ Sample cases created');

  // Create sample items
  const items = [
    {
      name: 'Common Knife',
      nameRu: 'Обычный нож',
      description: 'A basic knife',
      descriptionRu: 'Базовый нож',
      rarity: 'COMMON',
      type: 'ITEM',
      basePrice: 50,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Rare Pistol',
      nameRu: 'Редкий пистолет',
      description: 'A rare pistol',
      descriptionRu: 'Редкий пистолет',
      rarity: 'RARE',
      type: 'ITEM',
      basePrice: 200,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Epic Rifle',
      nameRu: 'Эпическая винтовка',
      description: 'An epic rifle',
      descriptionRu: 'Эпическая винтовка',
      rarity: 'EPIC',
      type: 'ITEM',
      basePrice: 500,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Legendary Sniper',
      nameRu: 'Легендарная снайперская винтовка',
      description: 'A legendary sniper rifle',
      descriptionRu: 'Легендарная снайперская винтовка',
      rarity: 'LEGENDARY',
      type: 'ITEM',
      basePrice: 2000,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Mythical Dragon',
      nameRu: 'Мифический дракон',
      description: 'A mythical dragon item',
      descriptionRu: 'Мифический предмет дракона',
      rarity: 'MYTHICAL',
      type: 'ITEM',
      basePrice: 10000,
      isCraftable: false,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Case Key',
      nameRu: 'Ключ от кейса',
      description: 'Opens special cases',
      descriptionRu: 'Открывает специальные кейсы',
      rarity: 'UNCOMMON',
      type: 'KEY',
      basePrice: 100,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    },
    {
      name: 'Luck Booster',
      nameRu: 'Бустер удачи',
      description: 'Increases drop rates',
      descriptionRu: 'Увеличивает шанс дропа',
      rarity: 'RARE',
      type: 'BOOSTER',
      basePrice: 300,
      isCraftable: true,
      craftFrom: [],
      craftAmount: 1
    }
  ];

  for (const itemData of items) {
    await prisma.item.upsert({
      where: { name: itemData.name },
      update: {},
      create: itemData
    });
  }

  console.log('✅ Sample items created');

  // Add items to cases
  const allItems = await prisma.item.findMany();
  
  // Common case items
  const commonItems = allItems.filter(item => ['COMMON', 'UNCOMMON'].includes(item.rarity));
  for (const item of commonItems) {
    await prisma.caseItem.upsert({
      where: {
        caseId_itemId: {
          caseId: commonCase.id,
          itemId: item.id
        }
      },
      update: {},
      create: {
        caseId: commonCase.id,
        itemId: item.id,
        dropRate: item.rarity === 'COMMON' ? 70 : 30,
        isGuaranteed: false
      }
    });
  }

  // Rare case items
  const rareItems = allItems.filter(item => ['UNCOMMON', 'RARE', 'EPIC'].includes(item.rarity));
  for (const item of rareItems) {
    await prisma.caseItem.upsert({
      where: {
        caseId_itemId: {
          caseId: rareCase.id,
          itemId: item.id
        }
      },
      update: {},
      create: {
        caseId: rareCase.id,
        itemId: item.id,
        dropRate: item.rarity === 'UNCOMMON' ? 50 : item.rarity === 'RARE' ? 35 : 15,
        isGuaranteed: false
      }
    });
  }

  // Legendary case items
  const legendaryItems = allItems.filter(item => ['EPIC', 'LEGENDARY', 'MYTHICAL'].includes(item.rarity));
  for (const item of legendaryItems) {
    await prisma.caseItem.upsert({
      where: {
        caseId_itemId: {
          caseId: legendaryCase.id,
          itemId: item.id
        }
      },
      update: {},
      create: {
        caseId: legendaryCase.id,
        itemId: item.id,
        dropRate: item.rarity === 'EPIC' ? 50 : item.rarity === 'LEGENDARY' ? 35 : 15,
        isGuaranteed: false
      }
    });
  }

  console.log('✅ Items added to cases');

  // Create craft recipes
  const craftRecipe = await prisma.item.upsert({
    where: { name: 'Crafted Epic Item' },
    update: {},
    create: {
      name: 'Crafted Epic Item',
      nameRu: 'Созданный эпический предмет',
      description: 'Crafted from common items',
      descriptionRu: 'Создан из обычных предметов',
      rarity: 'EPIC',
      type: 'ITEM',
      basePrice: 800,
      isCraftable: true,
      craftFrom: [commonItems[0]?.id || '', commonItems[1]?.id || ''],
      craftAmount: 3
    }
  });

  console.log('✅ Craft recipes created');

  // Create upgrade paths
  const upgradePath = await prisma.itemUpgrade.upsert({
    where: { id: 'upgrade-1' },
    update: {},
    create: {
      fromItemId: commonItems[0]?.id || '',
      toItemId: rareItems[0]?.id || '',
      successRate: 50,
      cost: 150,
      currency: 'STORM_COINS'
    }
  });

  console.log('✅ Upgrade paths created');

  // Create achievements
  const achievements = [
    {
      name: 'First Case',
      nameRu: 'Первый кейс',
      description: 'Open your first case',
      descriptionRu: 'Откройте свой первый кейс',
      reward: 100,
      xpReward: 50,
      requirement: JSON.stringify({ type: 'CASE_OPEN', count: 1 })
    },
    {
      name: 'Case Master',
      nameRu: 'Мастер кейсов',
      description: 'Open 100 cases',
      descriptionRu: 'Откройте 100 кейсов',
      reward: 1000,
      xpReward: 500,
      requirement: JSON.stringify({ type: 'CASE_OPEN', count: 100 })
    },
    {
      name: 'Trader',
      nameRu: 'Торговец',
      description: 'Complete 10 market trades',
      descriptionRu: 'Завершите 10 торговых сделок',
      reward: 500,
      xpReward: 250,
      requirement: JSON.stringify({ type: 'MARKET_TRADE', count: 10 })
    },
    {
      name: 'Social',
      nameRu: 'Социальный',
      description: 'Send 100 chat messages',
      descriptionRu: 'Отправьте 100 сообщений в чат',
      reward: 200,
      xpReward: 100,
      requirement: JSON.stringify({ type: 'CHAT_MESSAGE', count: 100 })
    }
  ];

  for (const achievementData of achievements) {
    await prisma.achievement.upsert({
      where: { name: achievementData.name },
      update: {},
      create: achievementData
    });
  }

  console.log('✅ Achievements created');

  // Create currency rates
  await prisma.currencyRate.upsert({
    where: {
      fromCurrency_toCurrency: {
        fromCurrency: 'STORM_COINS',
        toCurrency: 'PREMIUM_COINS'
      }
    },
    update: {},
    create: {
      fromCurrency: 'STORM_COINS',
      toCurrency: 'PREMIUM_COINS',
      rate: 100 // 100 Storm Coins = 1 Premium Coin
    }
  });

  console.log('✅ Currency rates created');

  // Create sample promo code
  await prisma.promoCode.upsert({
    where: { code: 'WELCOME100' },
    update: {},
    create: {
      code: 'WELCOME100',
      reward: 100,
      rewardType: 'BALANCE',
      maxUses: 1000,
      isActive: true
    }
  });

  console.log('✅ Promo codes created');

  console.log('🎉 Seed completed successfully!');
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });