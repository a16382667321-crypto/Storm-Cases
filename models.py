# models.py
# ============================================================
# STORM CASES - Database Models
# Версия: 2.0 (расширенная)
# Описание: Этот файл определяет все таблицы базы данных,
# необходимые для работы Telegram-бота и WebApp.
# Используется SQLAlchemy ORM.
# ============================================================

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey,
    Text, JSON, BigInteger, Index, UniqueConstraint, Table
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# ================= ПОЛЬЗОВАТЕЛИ =================
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    nickname = Column(String(64), nullable=False)
    server = Column(String(32), nullable=True)
    balance = Column(Float, default=0.0)
    is_admin = Column(Boolean, default=False)
    sound_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    vibration_enabled = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    next_exp = Column(Integer, default=100)
    stats = Column(JSON, default=dict)  # opened_cases, items_obtained, spent, earned, market_sales, pvp_wins и т.д.

    # Отношения
    warnings = relationship("UserWarning", back_populates="user", foreign_keys="UserWarning.user_id")
    inventory = relationship("InventoryItem", back_populates="owner")
    market_listings = relationship("MarketListing", back_populates="seller")
    chat_messages = relationship("ChatMessage", back_populates="sender")
    quests = relationship("UserQuest", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    daily_reward = relationship("DailyReward", uselist=False, back_populates="user")
    clan_memberships = relationship("ClanMember", back_populates="user")
    pvp_matches_as_player1 = relationship("PvPMatch", foreign_keys="PvPMatch.player1_id", back_populates="player1")
    pvp_matches_as_player2 = relationship("PvPMatch", foreign_keys="PvPMatch.player2_id", back_populates="player2")
    sent_gifts = relationship("Gift", foreign_keys="Gift.sender_id", back_populates="sender")
    received_gifts = relationship("Gift", foreign_keys="Gift.recipient_id", back_populates="recipient")
    transactions = relationship("TransactionHistory", back_populates="user")
    tickets = relationship("SupportTicket", back_populates="user")
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referrals_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred")
    skins = relationship("UserSkin", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    dialogs_as_user1 = relationship("Dialog", foreign_keys="Dialog.user1_id", back_populates="user1")
    dialogs_as_user2 = relationship("Dialog", foreign_keys="Dialog.user2_id", back_populates="user2")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, nickname='{self.nickname}')>"


# ================= СЕРВЕРЫ =================
class Server(Base):
    __tablename__ = 'servers'

    server_name = Column(String(32), primary_key=True)
    online = Column(Integer, default=0)
    is_online = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    max_players = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Server(name='{self.server_name}', online={self.online})>"


# ================= КЕЙСЫ =================
class Case(Base):
    __tablename__ = 'cases'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    icon = Column(String(16), nullable=False)  # эмодзи
    price = Column(Float, nullable=False)
    chances = Column(JSON, nullable=False)  # {"common": 0.7, "rare": 0.25, ...}
    items = Column(JSON, nullable=True)  # список id предметов, если нужно
    is_active = Column(Boolean, default=True)

    openings = relationship("CaseOpeningHistory", back_populates="case")

    def __repr__(self):
        return f"<Case(id='{self.id}', name='{self.name}', price={self.price})>"


# ================= ПРЕДМЕТЫ =================
class Item(Base):
    __tablename__ = 'items'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    icon = Column(String(16), nullable=False)
    rarity = Column(String(16), nullable=False)  # common, rare, epic, legendary, mythic
    base_price = Column(Float, default=0.0)
    description = Column(Text, nullable=True)

    inventory_entries = relationship("InventoryItem", back_populates="item")
    market_listings = relationship("MarketListing", back_populates="item")
    auctions = relationship("Auction", back_populates="item")

    def __repr__(self):
        return f"<Item(id='{self.id}', name='{self.name}', rarity='{self.rarity}')>"


# ================= ИНВЕНТАРЬ =================
class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    __table_args__ = (
        Index('ix_inventory_items_user_id', 'user_id'),
    )

    uid = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(String(32), ForeignKey('items.id'), nullable=False)
    rarity = Column(String(16), nullable=False)  # денормализовано для быстрого доступа
    timestamp = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="inventory")
    item = relationship("Item", back_populates="inventory_entries")

    def __repr__(self):
        return f"<InventoryItem(uid={self.uid}, user_id={self.user_id}, item_id='{self.item_id}')>"


# ================= РЫНОК =================
class MarketListing(Base):
    __tablename__ = 'market_listings'
    __table_args__ = (
        Index('ix_market_listings_status', 'status'),
    )

    uid = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(String(32), ForeignKey('items.id'), nullable=False)
    rarity = Column(String(16), nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String(16), default='active')  # active, sold, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User", back_populates="market_listings")
    item = relationship("Item", back_populates="market_listings")

    def __repr__(self):
        return f"<MarketListing(uid={self.uid}, price={self.price}, status='{self.status}')>"


# ================= ЧАТ =================
class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = (
        Index('ix_chat_messages_timestamp', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    server = Column(String(32), nullable=True)
    text = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender_id={self.sender_id})>"


# ================= КВЕСТЫ =================
class Quest(Base):
    __tablename__ = 'quests'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    reward = Column(Float, default=0.0)
    reward_item_id = Column(String(32), nullable=True)
    type = Column(String(32), nullable=False)  # open_cases, win_pvp, chat_messages и т.д.
    target = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    user_quests = relationship("UserQuest", back_populates="quest")

    def __repr__(self):
        return f"<Quest(id='{self.id}', name='{self.name}')>"


class UserQuest(Base):
    __tablename__ = 'user_quests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    quest_id = Column(String(32), ForeignKey('quests.id'), nullable=False)
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    claimed = Column(Boolean, default=False)

    user = relationship("User", back_populates="quests")
    quest = relationship("Quest", back_populates="user_quests")

    __table_args__ = (UniqueConstraint('user_id', 'quest_id', name='uq_user_quest'),)

    def __repr__(self):
        return f"<UserQuest(user_id={self.user_id}, quest_id='{self.quest_id}', progress={self.progress})>"


# ================= ДОСТИЖЕНИЯ =================
class Achievement(Base):
    __tablename__ = 'achievements'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(16), nullable=False)
    reward = Column(Float, default=0.0)
    criteria_type = Column(String(32), nullable=False)  # opened_cases, items_obtained, level, balance и т.д.
    criteria_value = Column(Integer, nullable=False)

    user_achievements = relationship("UserAchievement", back_populates="achievement")

    def __repr__(self):
        return f"<Achievement(id='{self.id}', name='{self.name}')>"


class UserAchievement(Base):
    __tablename__ = 'user_achievements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(String(32), ForeignKey('achievements.id'), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),)

    def __repr__(self):
        return f"<UserAchievement(user_id={self.user_id}, achievement_id='{self.user_id}')>"


# ================= ЕЖЕДНЕВНАЯ НАГРАДА =================
class DailyReward(Base):
    __tablename__ = 'daily_rewards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    last_claimed_date = Column(DateTime, nullable=True)
    streak = Column(Integer, default=0)

    user = relationship("User", back_populates="daily_reward")

    def __repr__(self):
        return f"<DailyReward(user_id={self.user_id}, streak={self.streak})>"


# ================= КЛАНЫ =================
class Clan(Base):
    __tablename__ = 'clans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    leader_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)

    members = relationship("ClanMember", back_populates="clan")
    leader = relationship("User", foreign_keys=[leader_id])

    def __repr__(self):
        return f"<Clan(id={self.id}, name='{self.name}')>"


class ClanMember(Base):
    __tablename__ = 'clan_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    clan_id = Column(Integer, ForeignKey('clans.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(16), default='member')  # leader, officer, member
    joined_at = Column(DateTime, default=datetime.utcnow)

    clan = relationship("Clan", back_populates="members")
    user = relationship("User", back_populates="clan_memberships")

    __table_args__ = (UniqueConstraint('clan_id', 'user_id', name='uq_clan_member'),)

    def __repr__(self):
        return f"<ClanMember(clan_id={self.clan_id}, user_id={self.user_id}, role='{self.role}')>"


# ================= PvP =================
class PvPMatch(Base):
    __tablename__ = 'pvp_matches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    player2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    winner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    stake = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    player1 = relationship("User", foreign_keys=[player1_id], back_populates="pvp_matches_as_player1")
    player2 = relationship("User", foreign_keys=[player2_id], back_populates="pvp_matches_as_player2")
    winner = relationship("User", foreign_keys=[winner_id])

    def __repr__(self):
        return f"<PvPMatch(id={self.id}, winner_id={self.winner_id})>"


# ================= АУКЦИОН =================
class Auction(Base):
    __tablename__ = 'auctions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(32), ForeignKey('items.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    current_bid = Column(Float, default=0.0)
    current_bidder_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(16), default='active')  # active, ended, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("Item", back_populates="auctions")
    seller = relationship("User", foreign_keys=[seller_id])
    current_bidder = relationship("User", foreign_keys=[current_bidder_id])
    bids = relationship("Bid", back_populates="auction")

    def __repr__(self):
        return f"<Auction(id={self.id}, status='{self.status}', current_bid={self.current_bid})>"


class Bid(Base):
    __tablename__ = 'bids'

    id = Column(Integer, primary_key=True, autoincrement=True)
    auction_id = Column(Integer, ForeignKey('auctions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    auction = relationship("Auction", back_populates="bids")
    user = relationship("User")

    def __repr__(self):
        return f"<Bid(id={self.id}, auction_id={self.auction_id}, amount={self.amount})>"


# ================= ЛИЧНЫЕ СООБЩЕНИЯ =================
class Dialog(Base):
    __tablename__ = 'dialogs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user1 = relationship("User", foreign_keys=[user1_id], back_populates="dialogs_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="dialogs_as_user2")
    messages = relationship("PrivateMessage", back_populates="dialog")

    __table_args__ = (UniqueConstraint('user1_id', 'user2_id', name='uq_dialog_users'),)

    def __repr__(self):
        return f"<Dialog(id={self.id}, user1={self.user1_id}, user2={self.user2_id})>"


class PrivateMessage(Base):
    __tablename__ = 'private_messages'
    __table_args__ = (
        Index('ix_private_messages_dialog_id', 'dialog_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    dialog_id = Column(Integer, ForeignKey('dialogs.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)

    dialog = relationship("Dialog", back_populates="messages")
    sender = relationship("User")

    def __repr__(self):
        return f"<PrivateMessage(id={self.id}, dialog_id={self.dialog_id})>"


# ================= СОБЫТИЯ =================
class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    reward = Column(Float, default=0.0)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Event(id={self.id}, name='{self.name}')>"


# ================= ПОДПИСКИ =================
class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan = Column(String(32), nullable=False)  # vip, premium
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)

    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan='{self.plan}')>"


# ================= ПОДАРКИ =================
class Gift(Base):
    __tablename__ = 'gifts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_gifts")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_gifts")

    def __repr__(self):
        return f"<Gift(id={self.id}, from={self.sender_id}, to={self.recipient_id}, amount={self.amount})>"


# ================= ИСТОРИЯ ТРАНЗАКЦИЙ =================
class TransactionHistory(Base):
    __tablename__ = 'transaction_history'
    __table_args__ = (
        Index('ix_transaction_history_user_id', 'user_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(32), nullable=False)  # open_case, sell_item, buy_market, donate, etc.
    amount = Column(Float, default=0.0)  # positive = доход, negative = расход
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<TransactionHistory(id={self.id}, user_id={self.user_id}, type='{self.type}', amount={self.amount})>"


# ================= ТИКЕТЫ ПОДДЕРЖКИ =================
class SupportTicket(Base):
    __tablename__ = 'support_tickets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject = Column(String(128), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(16), default='open')  # open, in_progress, closed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="tickets")
    replies = relationship("SupportTicketReply", back_populates="ticket")

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class SupportTicketReply(Base):
    __tablename__ = 'support_ticket_replies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="replies")
    sender = relationship("User")

    def __repr__(self):
        return f"<SupportTicketReply(id={self.id}, ticket_id={self.ticket_id}, is_admin={self.is_admin})>"


# ================= ПРОМОКОДЫ =================
class PromoCode(Base):
    __tablename__ = 'promo_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False)
    reward_type = Column(String(16), nullable=False)  # coins, item, etc.
    reward_amount = Column(Float, default=0.0)
    reward_item_id = Column(String(32), nullable=True)
    uses_left = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<PromoCode(id={self.id}, code='{self.code}')>"


# ================= РЕФЕРАЛЬНАЯ СИСТЕМА =================
class Referral(Base):
    __tablename__ = 'referrals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referred_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    bonus_percent = Column(Float, default=10.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")

    def __repr__(self):
        return f"<Referral(id={self.id}, referrer={self.referrer_id}, referred={self.referred_id})>"


# ================= ПРЕДУПРЕЖДЕНИЯ =================
class UserWarning(Base):
    __tablename__ = 'user_warnings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="warnings")
    admin = relationship("User", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<UserWarning(id={self.id}, user_id={self.user_id}, admin_id={self.admin_id})>"


# ================= ЛОГИ АДМИНИСТРАТОРА =================
class AdminActionLog(Base):
    __tablename__ = 'admin_action_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    admin = relationship("User")

    def __repr__(self):
        return f"<AdminActionLog(id={self.id}, admin_id={self.admin_id}, action='{self.action}')>"


# ================= СКИНЫ =================
class Skin(Base):
    __tablename__ = 'skins'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    icon = Column(String(16), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    user_skins = relationship("UserSkin", back_populates="skin")

    def __repr__(self):
        return f"<Skin(id='{self.id}', name='{self.name}')>"


class UserSkin(Base):
    __tablename__ = 'user_skins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    skin_id = Column(String(32), ForeignKey('skins.id'), nullable=False)
    equipped = Column(Boolean, default=False)

    user = relationship("User", back_populates="skins")
    skin = relationship("Skin", back_populates="user_skins")

    __table_args__ = (UniqueConstraint('user_id', 'skin_id', name='uq_user_skin'),)

    def __repr__(self):
        return f"<UserSkin(user_id={self.user_id}, skin_id='{self.skin_id}')>"


# ================= РЕЦЕПТЫ КРАФТА =================
class CraftRecipe(Base):
    __tablename__ = 'craft_recipes'

    id = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    result_rarity = Column(String(16), nullable=False)
    cost = Column(JSON, nullable=False)  # {"common": 5, "rare": 2}
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<CraftRecipe(id='{self.id}', name='{self.name}')>"


# ================= ИСТОРИЯ ОТКРЫТИЯ КЕЙСОВ =================
class CaseOpeningHistory(Base):
    __tablename__ = 'case_opening_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    case_id = Column(String(32), ForeignKey('cases.id'), nullable=False)
    item_id = Column(String(32), ForeignKey('items.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    case = relationship("Case", back_populates="openings")
    item = relationship("Item")

    def __repr__(self):
        return f"<CaseOpeningHistory(id={self.id}, user_id={self.user_id}, case_id='{self.case_id}')>"


# ================= СЛОТЫ =================
class SlotSpin(Base):
    __tablename__ = 'slot_spins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    symbols = Column(JSON, nullable=False)  # список из трёх символов
    win_amount = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

    def __repr__(self):
        return f"<SlotSpin(id={self.id}, user_id={self.user_id}, win={self.win_amount})>"


# ================= КОЛЕСО ФОРТУНЫ =================
class WheelPrize(Base):
    __tablename__ = 'wheel_prizes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    probability = Column(Float, nullable=False)
    reward_type = Column(String(16), nullable=False)  # coins, item, nothing
    reward_amount = Column(Float, default=0.0)
    reward_item_id = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<WheelPrize(id={self.id}, name='{self.name}')>"


class WheelSpinHistory(Base):
    __tablename__ = 'wheel_spin_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    prize_id = Column(Integer, ForeignKey('wheel_prizes.id'), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    prize = relationship("WheelPrize")

    def __repr__(self):
        return f"<WheelSpinHistory(id={self.id}, user_id={self.user_id}, prize_id={self.prize_id})>"
