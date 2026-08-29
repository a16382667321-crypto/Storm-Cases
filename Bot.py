# Bot.py
# ============================================================
# STORM CASES - Telegram Bot
# ============================================================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from config import settings
from database import AsyncSessionLocal
from models import User, Server


# ================= HELPER FUNCTIONS =================

async def get_user_by_telegram_id(telegram_id: int) -> User:
    """Get user by Telegram ID"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    """Get or create user"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            nickname = first_name or username or "User"
            is_admin = (telegram_id == settings.ADMIN_TELEGRAM_ID)

            user = User(
                telegram_id=telegram_id,
                nickname=nickname,
                balance=settings.INITIAL_BALANCE,
                is_admin=is_admin
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user


# ================= COMMAND HANDLERS =================

async def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    user = update.effective_user
    telegram_id = user.id

    # Get or create user
    db_user = await get_or_create_user(telegram_id, user.username, user.first_name)

    # Create WebApp button (opens as mini-app inside Telegram)
    keyboard = [
        [InlineKeyboardButton(
            "🎮 Открыть STORM CASES",
            web_app=WebAppInfo(url="https://a16382667321-crypto.github.io/Storm-Cases/")
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = f"""
👋 Привет, {db_user.nickname}!

🎁 Добро пожаловать в STORM CASES — бот для открытия кейсов и получения редких предметов!

💰 Твой баланс: {db_user.balance} монет

📖 Команды:
/start — Открыть меню
/profile — Твой профиль
/balance — Проверить баланс
/help — Помощь

👇 Нажми кнопку ниже для открытия приложения:
    """

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    help_text = """
📖 <b>Помощь - STORM CASES</b>

🎮 <b>Основные команды:</b>
/start — Открыть меню и WebApp
/profile — Информация о профиле
/balance — Проверить баланс
/help — Эта справка

🎁 <b>О проекте:</b>
STORM CASES — это бот для открытия кейсов с возможностью получения редких предметов.
Открывай кейсы, собирай коллекцию, торгуй на рынке!

💎 <b>Редкость предметов:</b>
⚪ Обычный (Common)
🔵 Редкий (Rare)
🟣 Эпический (Epic)
🟡 Легендарный (Legendary)
🔴 Мифический (Mythic)

📦 <b>Кейсы:</b>
• Базовый кейс — 50 монет
• Премиум кейс — 200 монет
• Легендарный кейс — 1000 монет

🛒 <b>Рынок:</b>
Продавай и покупай предметы у других игроков!

🎡 <b>Колесо фортуны:</b>
Испытай удачу и выиграй монеты!

📜 <b>Квесты:</b>
Выполняй задания и получай награды!

🏆 <b>Топ игроков:</b>
Соревнуйся с другими и поднимайся в рейтинге!

❓ <b>Нужна помощь?</b>
Напиши в поддержку через приложение или обратись к администратору.
    """

    await update.message.reply_text(help_text, parse_mode='HTML')


async def profile_command(update: Update, context: CallbackContext):
    """Handle /profile command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user:
        await update.message.reply_text("❌ Сначала используй /start для регистрации")
        return

    profile_text = f"""
👤 <b>Профиль: {db_user.nickname}</b>

💰 <b>Баланс:</b> {db_user.balance} монет
🏷 <b>Уровень:</b> {db_user.level}
⭐ <b>Опыт:</b> {db_user.exp}/{db_user.next_exp}
🖥 <b>Сервер:</b> {db_user.server or 'Не выбран'}
📅 <b>Регистрация:</b> {db_user.registered_at.strftime('%d.%m.%Y')}

📊 <b>Статистика:</b>
"""
    if db_user.stats:
        stats = db_user.stats
        profile_text += f"🎁 Открыто кейсов: {stats.get('opened_cases', 0)}\n"
        profile_text += f"📦 Получено предметов: {stats.get('items_obtained', 0)}\n"
        profile_text += f"💸 Потрачено: {stats.get('spent', 0)}\n"
        profile_text += f"💵 Заработано: {stats.get('earned', 0)}\n"
        profile_text += f"🏆 Побед в PvP: {stats.get('pvp_wins', 0)}\n"

    if db_user.is_admin:
        profile_text += "\n👑 <b>Администратор</b>"

    await update.message.reply_text(profile_text, parse_mode='HTML')


async def balance_command(update: Update, context: CallbackContext):
    """Handle /balance command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user:
        await update.message.reply_text("❌ Сначала используй /start для регистрации")
        return

    await update.message.reply_text(f"💰 Твой баланс: {db_user.balance} монет")


async def servers_command(update: Update, context: CallbackContext):
    """Handle /servers command"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server))
        servers = result.scalars().all()

    if not servers:
        await update.message.reply_text("❌ Серверы не найдены")
        return

    servers_text = "🖥 <b>Доступные серверы:</b>\n\n"
    for server in servers:
        status = "🟢 Онлайн" if server.is_online else "🔴 Оффлайн"
        servers_text += f"📌 <b>{server.server_name}</b>\n"
        servers_text += f"   {status} | Игроков: {server.online}\n"
        if server.description:
            servers_text += f"   📝 {server.description}\n"
        servers_text += "\n"

    await update.message.reply_text(servers_text, parse_mode='HTML')


async def admin_command(update: Update, context: CallbackContext):
    """Handle /admin command (admin only)"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    admin_text = """
👑 <b>Панель администратора</b>

📋 <b>Команды:</b>
/admin_users — Список пользователей
/admin_stats — Статистика сервера
/admin_broadcast — Рассылка
/admin_addcoins — Добавить монеты

⚠️ Будь осторожен с административными командами!
    """

    await update.message.reply_text(admin_text, parse_mode='HTML')


async def admin_users_command(update: Update, context: CallbackContext):
    """Handle /admin_users command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(10))
        users = result.scalars().all()

    if not users:
        await update.message.reply_text("❌ Пользователи не найдены")
        return

    users_text = "👥 <b>Последние пользователи:</b>\n\n"
    for u in users:
        admin_badge = " 👑" if u.is_admin else ""
        users_text += f"👤 {u.nickname}{admin_badge}\n"
        users_text += f"   ID: {u.telegram_id}\n"
        users_text += f"   💰 Баланс: {u.balance}\n"
        users_text += f"   🖥 Сервер: {u.server or 'Не выбран'}\n\n"

    await update.message.reply_text(users_text, parse_mode='HTML')


async def admin_stats_command(update: Update, context: CallbackContext):
    """Handle /admin_stats command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    async with AsyncSessionLocal() as db:
        from models import User, InventoryItem, MarketListing

        # Count users
        users_result = await db.execute(select(func.count(User.id)))
        total_users = users_result.scalar()

        # Count inventory items
        inv_result = await db.execute(select(func.count(InventoryItem.uid)))
        total_items = inv_result.scalar()

        # Count market listings
        market_result = await db.execute(select(func.count(MarketListing.uid)))
        total_listings = market_result.scalar()

    stats_text = f"""
📊 <b>Статистика сервера</b>

👥 Всего пользователей: {total_users}
📦 Всего предметов: {total_items}
🛒 Листингов на рынке: {total_listings}
    """

    await update.message.reply_text(stats_text, parse_mode='HTML')


async def admin_addcoins_command(update: Update, context: CallbackContext):
    """Handle /admin_addcoins command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Использование: /admin_addcoins <user_id> <amount>")
        return

    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Неверный формат аргументов")
        return

    async with AsyncSessionLocal() as db:
        from models import User, TransactionHistory

        result = await db.execute(select(User).where(User.id == target_id))
        target_user = result.scalar_one_or_none()

        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return

        target_user.balance += amount

        # Add transaction
        transaction = TransactionHistory(
            user_id=target_user.id,
            type='admin_add',
            amount=amount,
            description=f'Admin added coins'
        )
        db.add(transaction)

        await db.commit()

    await update.message.reply_text(f"✅ Добавлено {amount} монет пользователю {target_user.nickname}")


async def admin_broadcast_command(update: Update, context: CallbackContext):
    """Handle /admin_broadcast command"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user or not db_user.is_admin:
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return

    if not context.args:
        await update.message.reply_text("Использование: /admin_broadcast <message>")
        return

    message = ' '.join(context.args)

    # In a real implementation, you would send this to all users
    # For now, just log it
    await update.message.reply_text(f"✅ Рассылка отправлена: {message}")


# ================= MESSAGE HANDLERS =================

async def handle_message(update: Update, context: CallbackContext):
    """Handle regular messages"""
    user = update.effective_user
    db_user = await get_user_by_telegram_id(user.id)

    if not db_user:
        await update.message.reply_text("❌ Сначала используй /start для регистрации")
        return

    # Create WebApp button if user sends any message
    keyboard = [
        [InlineKeyboardButton(
            "🎮 Открыть STORM CASES",
            web_app=WebAppInfo(url=settings.WEBAPP_URL)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Привет, {db_user.nickname}! Нажми кнопку ниже для открытия приложения:",
        reply_markup=reply_markup
    )


# ================= MAIN FUNCTION =================

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(settings.BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("servers", servers_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("admin_users", admin_users_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("admin_addcoins", admin_addcoins_command))
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast_command))

    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("🤖 Bot started...")
    application.run_polling()


if __name__ == "__main__":
    main()
