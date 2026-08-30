import TelegramBot from 'node-telegram-bot-api';
import prisma from '../config/database';
import { generateAuthToken } from '../utils/jwt';

const token = process.env.TELEGRAM_BOT_TOKEN;
if (!token) {
  throw new Error('TELEGRAM_BOT_TOKEN is not defined');
}

const bot = new TelegramBot(token, { polling: true });

export function setupTelegramBot() {
  // Start command
  bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramId = msg.from?.id.toString();
    
    if (!telegramId) return;

    try {
      // Check if user exists
      let user = await prisma.user.findUnique({
        where: { telegramId }
      });

      if (!user) {
        // Create new user
        user = await prisma.user.create({
          data: {
            telegramId,
            username: msg.from?.username,
            firstName: msg.from?.first_name,
            lastName: msg.from?.last_name,
            languageCode: msg.from?.language_code,
            isBot: msg.from?.is_bot || false,
            referralCode: generateReferralCode()
          }
        });
      }

      // Generate auth token for Mini App
      const authToken = generateAuthToken(user.id);

      const welcomeMessage = `
🎉 Добро пожаловать в Storm Cases!

🎰 Открывай кейсы и получай ценные предметы
📦 Управляй инвентарем и крафти новые предметы
💡 Торгуй на рынке с другими игроками
💬 Общайся в чате с сообществом

🔗 Нажми кнопку ниже для открытия Mini App
      `;

      const keyboard = {
        inline_keyboard: [
          [
            {
              text: '🎮 Открыть Storm Cases',
              web_app: {
                url: `${process.env.MINI_APP_URL}?token=${authToken}`
              }
            }
          ],
          [
            { text: '📋 Помощь', callback_data: 'help' },
            { text: '⚙️ Настройки', callback_data: 'settings' }
          ]
        ]
      };

      await bot.sendMessage(chatId, welcomeMessage, {
        reply_markup: keyboard,
        parse_mode: 'HTML'
      });

    } catch (error) {
      console.error('Error in /start command:', error);
      await bot.sendMessage(chatId, '❌ Произошла ошибка. Попробуйте позже.');
    }
  });

  // Help command
  bot.onText(/\/help/, async (msg) => {
    const chatId = msg.chat.id;
    const helpMessage = `
📚 <b>Справка по Storm Cases</b>

🎰 <b>Кейсы</b> - Открывайте кейсы разной редкости
📦 <b>Инвентарь</b> - Просматривайте и крафтите предметы
💰 <b>Рынок</b> - Покупайте и продавайте предметы
💬 <b>Чат</b> - Общайтесь с другими игроками
⚙️ <b>Настройки</b> - Настройте профиль и техподдержку

❓ Если у вас есть вопросы, используйте техподдержку в настройках.
    `;

    await bot.sendMessage(chatId, helpMessage, { parse_mode: 'HTML' });
  });

  // Settings command
  bot.onText(/\/settings/, async (msg) => {
    const chatId = msg.chat.id;
    const settingsMessage = `
⚙️ <b>Настройки</b>

Для доступа к настройкам откройте Mini App и перейдите во вкладку "Настройки".

Там вы можете:
• Изменить профиль
• Настроить уведомления
• Связаться с техподдержкой
• Получить доступ к админ-панели
    `;

    await bot.sendMessage(chatId, settingsMessage, { parse_mode: 'HTML' });
  });

  // Callback query handler
  bot.on('callback_query', async (query) => {
    const chatId = query.message?.chat.id;
    const data = query.data;

    if (!chatId || !data) return;

    try {
      switch (data) {
        case 'help':
          await bot.sendMessage(chatId, 'Используйте команду /help для получения справки');
          break;
        case 'settings':
          await bot.sendMessage(chatId, 'Используйте команду /settings для доступа к настройкам');
          break;
        default:
          await bot.answerCallbackQuery(query.id, { text: 'Неизвестная команда' });
      }
      
      await bot.answerCallbackQuery(query.id);
    } catch (error) {
      console.error('Error handling callback query:', error);
    }
  });

  // Error handling
  bot.on('polling_error', (error) => {
    console.error('Telegram bot polling error:', error);
  });

  console.log('✅ Telegram bot initialized');
}

function generateReferralCode(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 8; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}

export default bot;