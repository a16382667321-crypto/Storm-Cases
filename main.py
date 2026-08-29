# main.py
# ============================================================
# STORM CASES - FastAPI Backend
# ============================================================

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional, List
import random
import json
import urllib.parse

from config import settings
from database import get_db, init_db, AsyncSessionLocal
from models import (
    User, Server, Case, Item, InventoryItem, MarketListing, ChatMessage,
    Quest, UserQuest, Achievement, UserAchievement, DailyReward, Clan,
    ClanMember, PvPMatch, Auction, Bid, Dialog, PrivateMessage, Event,
    Subscription, Gift, TransactionHistory, SupportTicket, SupportTicketReply, PromoCode,
    Referral, UserWarning, AdminActionLog, Skin, UserSkin, CraftRecipe,
    CaseOpeningHistory, SlotSpin, WheelPrize, WheelSpinHistory
)

app = FastAPI(title="STORM CASES API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= HELPER FUNCTIONS =================

def parse_telegram_data(init_data: str) -> dict:
    """Parse Telegram WebApp init data"""
    try:
        data = {}
        for pair in init_data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                data[key] = urllib.parse.unquote(value)
        
        if 'user' in data:
            user_data = json.loads(data['user'])
            return user_data
        return {}
    except Exception as e:
        print(f"Error parsing init data: {e}")
        return {}

async def get_user_from_init_data(
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get user from Telegram init data"""
    user_data = parse_telegram_data(init_data)
    telegram_id = user_data.get('id')
    
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

async def add_transaction(
    db: AsyncSession,
    user_id: int,
    transaction_type: str,
    amount: float,
    description: str = None
):
    """Add transaction to history"""
    transaction = TransactionHistory(
        user_id=user_id,
        type=transaction_type,
        amount=amount,
        description=description
    )
    db.add(transaction)

async def update_user_stats(db: AsyncSession, user: User, stat_key: str, value: int = 1):
    """Update user stats"""
    if not user.stats:
        user.stats = {}
    user.stats[stat_key] = user.stats.get(stat_key, 0) + value

# ================= API ENDPOINTS =================

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the WebApp"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>index.html not found</h1>"

@app.post("/api/register")
async def register_user(
    init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db)
):
    """Register or get existing user"""
    user_data = parse_telegram_data(init_data)
    telegram_id = user_data.get('id')
    
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Invalid init data")
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        return {"status": "ok", "user_id": user.id}
    
    # Create new user
    nickname = user_data.get('first_name', 'User')
    if user_data.get('last_name'):
        nickname += f" {user_data['last_name']}"
    
    # Check if admin
    is_admin = (telegram_id == settings.ADMIN_TELEGRAM_ID)
    
    user = User(
        telegram_id=telegram_id,
        nickname=nickname,
        balance=settings.INITIAL_BALANCE,
        is_admin=is_admin,
        registered_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return {"status": "ok", "user_id": user.id}

@app.get("/api/state")
async def get_state(
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Get complete user state"""
    # Load user with relationships
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.inventory),
            selectinload(User.warnings),
            selectinload(User.achievements).selectinload(UserAchievement.achievement),
            selectinload(User.daily_reward),
            selectinload(User.quests).selectinload(UserQuest.quest),
            selectinload(User.skins).selectinload(UserSkin.skin),
            selectinload(User.subscriptions)
        )
        .where(User.id == user.id)
    )
    user = result.scalar_one()
    
    # Get cases
    cases_result = await db.execute(
        select(Case).where(Case.is_active == True)
    )
    cases = cases_result.scalars().all()
    
    # Get market listings
    market_result = await db.execute(
        select(MarketListing)
        .options(selectinload(MarketListing.item), selectinload(MarketListing.seller))
        .where(MarketListing.status == 'active')
    )
    market = market_result.scalars().all()
    
    # Get chat messages
    chat_result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.sender))
        .where(ChatMessage.server == user.server)
        .order_by(ChatMessage.timestamp.desc())
        .limit(50)
    )
    chat = chat_result.scalars().all()
    
    # Get items grouped by rarity
    items_result = await db.execute(select(Item))
    all_items = items_result.scalars().all()
    items_by_rarity = {}
    for item in all_items:
        if item.rarity not in items_by_rarity:
            items_by_rarity[item.rarity] = []
        items_by_rarity[item.rarity].append({
            'id': item.id,
            'name': item.name,
            'icon': item.icon,
            'rarity': item.rarity
        })
    
    # Get dialogs
    dialogs_result = await db.execute(
        select(Dialog)
        .options(selectinload(Dialog.messages))
        .where(or_(Dialog.user1_id == user.id, Dialog.user2_id == user.id))
    )
    dialogs = []
    for dialog in dialogs_result.scalars():
        partner_id = dialog.user2_id if dialog.user1_id == user.id else dialog.user1_id
        partner_result = await db.execute(select(User).where(User.id == partner_id))
        partner = partner_result.scalar_one_or_none()
        messages = dialog.messages if dialog.messages else []
        last_message = messages[-1].text if messages else ""
        unread = sum(1 for m in messages if not m.read and m.sender_id != user.id)
        
        dialogs.append({
            'id': dialog.id,
            'partner_nick': partner.nickname if partner else 'Unknown',
            'last_message': last_message,
            'unread': unread
        })
    
    # Get events
    events_result = await db.execute(
        select(Event).where(Event.is_active == True)
    )
    events = events_result.scalars().all()
    
    # Get server stats
    server_stats = {
        'online': random.randint(50, 200),
        'total_users': 0,
        'total_cases_opened': 0
    }
    
    # Get history
    history_result = await db.execute(
        select(TransactionHistory)
        .where(TransactionHistory.user_id == user.id)
        .order_by(TransactionHistory.timestamp.desc())
        .limit(20)
    )
    history = history_result.scalars().all()
    
    return {
        'user': {
            'id': user.id,
            'nickname': user.nickname,
            'balance': user.balance,
            'server': user.server,
            'is_admin': user.is_admin,
            'sound_enabled': user.sound_enabled,
            'notifications_enabled': user.notifications_enabled,
            'vibration_enabled': user.vibration_enabled,
            'registered_at': int(user.registered_at.timestamp()),
            'level': user.level,
            'exp': user.exp,
            'next_exp': user.next_exp,
            'stats': user.stats or {},
            'inventory': [
                {
                    'uid': inv.uid,
                    'item_id': inv.item_id,
                    'rarity': inv.rarity,
                    'timestamp': int(inv.timestamp.timestamp())
                }
                for inv in user.inventory
            ],
            'warnings': [
                {'reason': w.reason, 'timestamp': int(w.timestamp.timestamp())}
                for w in user.warnings
            ],
            'achievements': [
                {
                    'name': a.achievement.name,
                    'icon': a.achievement.icon,
                    'description': a.achievement.description
                }
                for a in user.achievements
            ]
        },
        'cases': [
            {
                'id': c.id,
                'name': c.name,
                'icon': c.icon,
                'price': c.price,
                'chances': c.chances
            }
            for c in cases
        ],
        'items': items_by_rarity,
        'market': [
            {
                'uid': m.uid,
                'item_id': m.item_id,
                'rarity': m.rarity,
                'price': m.price,
                'seller_id': m.seller_id,
                'seller_nick': m.seller.nickname
            }
            for m in market
        ],
        'chat': [
            {
                'id': c.id,
                'sender_nick': c.sender.nickname,
                'text': c.text,
                'timestamp': int(c.timestamp.timestamp())
            }
            for c in reversed(chat)
        ],
        'quests': [
            {
                'id': q.quest.id,
                'name': q.quest.name,
                'description': q.quest.description,
                'reward': q.quest.reward,
                'progress': q.progress,
                'target': q.quest.target,
                'completed': q.completed,
                'claimed': q.claimed
            }
            for q in user.quests
        ],
        'dialogs': dialogs,
        'events': [
            {
                'name': e.name,
                'description': e.description,
                'reward': e.reward
            }
            for e in events
        ],
        'server_stats': server_stats,
        'history': [
            {
                'type': h.type,
                'amount': h.amount,
                'timestamp': int(h.timestamp.timestamp())
            }
            for h in history
        ],
        'rarity_labels': {
            'common': 'Обычный',
            'rare': 'Редкий',
            'epic': 'Эпический',
            'legendary': 'Легендарный',
            'mythic': 'Мифический'
        },
        'server_settings': {
            'sell_multiplier': settings.SELL_MULTIPLIER
        }
    }

@app.get("/api/servers")
async def get_servers(db: AsyncSession = Depends(get_db)):
    """Get available servers"""
    result = await db.execute(select(Server))
    servers = result.scalars().all()
    
    return {
        'servers': [
            {
                'server_name': s.server_name,
                'online': s.online,
                'is_online': s.is_online,
                'description': s.description
            }
            for s in servers
        ]
    }

# ================= SUPPORT TICKETS API =================

@app.get("/api/support/tickets")
async def get_support_tickets(
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Get user's support tickets"""
    result = await db.execute(
        select(SupportTicket)
        .options(selectinload(SupportTicket.replies))
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    
    return {
        "tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "message": t.message,
                "status": t.status,
                "created_at": int(t.created_at.timestamp()),
                "replies": [
                    {
                        "id": r.id,
                        "message": r.message,
                        "is_admin": r.is_admin,
                        "sender_nick": r.sender.nickname if r.sender else "Unknown",
                        "created_at": int(r.created_at.timestamp())
                    }
                    for r in t.replies
                ]
            }
            for t in tickets
        ]
    }

@app.get("/api/support/tickets/all")
async def get_all_support_tickets(
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Get all support tickets (admin only)"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.execute(
        select(SupportTicket)
        .options(selectinload(SupportTicket.user), selectinload(SupportTicket.replies))
        .order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    
    return {
        "tickets": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "user_nick": t.user.nickname,
                "subject": t.subject,
                "message": t.message,
                "status": t.status,
                "created_at": int(t.created_at.timestamp()),
                "replies": [
                    {
                        "id": r.id,
                        "message": r.message,
                        "is_admin": r.is_admin,
                        "sender_nick": r.sender.nickname if r.sender else "Unknown",
                        "created_at": int(r.created_at.timestamp())
                    }
                    for r in t.replies
                ]
            }
            for t in tickets
        ]
    }

@app.post("/api/support/tickets/{ticket_id}/reply")
async def reply_to_ticket(
    ticket_id: int,
    reply_data: dict,
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Reply to a support ticket"""
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check permissions
    if not user.is_admin and ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    message = reply_data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Create reply
    reply = SupportTicketReply(
        ticket_id=ticket_id,
        sender_id=user.id,
        message=message,
        is_admin=user.is_admin
    )
    db.add(reply)
    
    # Update ticket status if admin replies
    if user.is_admin and ticket.status == "open":
        ticket.status = "in_progress"
    
    await db.commit()
    
    return {"status": "ok"}

@app.put("/api/support/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    status_data: dict,
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Update ticket status (admin only)"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_status = status_data.get("status")
    if new_status not in ["open", "in_progress", "closed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    ticket.status = new_status
    await db.commit()
    
    return {"status": "ok"}

@app.post("/api/action")
async def perform_action(
    action_data: dict,
    user: User = Depends(get_user_from_init_data),
    db: AsyncSession = Depends(get_db)
):
    """Perform various user actions"""
    action_type = action_data.get('type')
    
    if action_type == 'change_server':
        return await action_change_server(user, action_data, db)
    elif action_type == 'open_case':
        return await action_open_case(user, action_data, db)
    elif action_type == 'sell_item':
        return await action_sell_item(user, action_data, db)
    elif action_type == 'list_market':
        return await action_list_market(user, action_data, db)
    elif action_type == 'buy_market':
        return await action_buy_market(user, action_data, db)
    elif action_type == 'cancel_listing':
        return await action_cancel_listing(user, action_data, db)
    elif action_type == 'send_chat':
        return await action_send_chat(user, action_data, db)
    elif action_type == 'craft':
        return await action_craft(user, action_data, db)
    elif action_type == 'buy_subscription':
        return await action_buy_subscription(user, action_data, db)
    elif action_type == 'send_gift':
        return await action_send_gift(user, action_data, db)
    elif action_type == 'card_payment':
        return await action_card_payment(user, action_data, db)
    elif action_type == 'place_bid':
        return await action_place_bid(user, action_data, db)
    elif action_type == 'send_private_message':
        return await action_send_private_message(user, action_data, db)
    elif action_type == 'toggle_sound':
        return await action_toggle_sound(user, db)
    elif action_type == 'toggle_notifications':
        return await action_toggle_notifications(user, db)
    elif action_type == 'toggle_vibration':
        return await action_toggle_vibration(user, db)
    elif action_type == 'claim_daily':
        return await action_claim_daily(user, db)
    elif action_type == 'claim_quest':
        return await action_claim_quest(user, action_data, db)
    elif action_type == 'spin_wheel':
        return await action_spin_wheel(user, db)
    elif action_type == 'spin_slots':
        return await action_spin_slots(user, action_data, db)
    elif action_type == 'start_pvp':
        return await action_start_pvp(user, action_data, db)
    elif action_type == 'create_clan':
        return await action_create_clan(user, action_data, db)
    elif action_type == 'join_clan':
        return await action_join_clan(user, action_data, db)
    elif action_type == 'equip_skin':
        return await action_equip_skin(user, action_data, db)
    elif action_type == 'activate_promo':
        return await action_activate_promo(user, action_data, db)
    elif action_type == 'submit_ticket':
        return await action_submit_ticket(user, action_data, db)
    elif action_type == 'admin_ban_user':
        return await action_admin_ban_user(user, action_data, db)
    elif action_type == 'admin_broadcast':
        return await action_admin_broadcast(user, action_data, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")

# ================= ACTION HANDLERS =================

async def action_change_server(user: User, data: dict, db: AsyncSession):
    """Change user's server"""
    server_name = data.get('server')
    
    # Check if server exists
    result = await db.execute(
        select(Server).where(Server.server_name == server_name)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    user.server = server_name
    await db.commit()
    
    return {"status": "ok"}

async def action_open_case(user: User, data: dict, db: AsyncSession):
    """Open a case"""
    case_id = data.get('case_id')
    
    # Get case
    result = await db.execute(
        select(Case).where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if user.balance < case.price:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct balance
    user.balance -= case.price
    
    # Select random item based on chances
    rand = random.random()
    cumulative = 0.0
    selected_rarity = 'common'
    
    for rarity, chance in case.chances.items():
        cumulative += chance
        if rand <= cumulative:
            selected_rarity = rarity
            break
    
    # Get random item of that rarity
    items_result = await db.execute(
        select(Item).where(Item.rarity == selected_rarity)
    )
    items = items_result.scalars().all()
    
    if not items:
        selected_rarity = 'common'
        items_result = await db.execute(
            select(Item).where(Item.rarity == 'common')
        )
        items = items_result.scalars().all()
    
    item = random.choice(items)
    
    # Add to inventory
    inv_item = InventoryItem(
        user_id=user.id,
        item_id=item.id,
        rarity=item.rarity
    )
    db.add(inv_item)
    
    # Record history
    history = CaseOpeningHistory(
        user_id=user.id,
        case_id=case_id,
        item_id=item.id
    )
    db.add(history)
    
    # Update stats
    await update_user_stats(db, user, 'opened_cases')
    await update_user_stats(db, user, 'items_obtained')
    await update_user_stats(db, user, 'spent', case.price)
    
    # Add transaction
    await add_transaction(db, user.id, 'open_case', -case.price, f"Opened {case.name}")
    
    await db.commit()
    await db.refresh(inv_item)
    
    return {
        "status": "ok",
        "item": {
            "id": item.id,
            "name": item.name,
            "icon": item.icon,
            "rarity": item.rarity
        }
    }

async def action_sell_item(user: User, data: dict, db: AsyncSession):
    """Sell item from inventory"""
    uid = data.get('uid')
    
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(and_(InventoryItem.uid == uid, InventoryItem.user_id == user.id))
    )
    inv_item = result.scalar_one_or_none()
    
    if not inv_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Calculate sell price
    sell_price = inv_item.item.base_price * settings.SELL_MULTIPLIER
    
    # Add balance
    user.balance += sell_price
    
    # Remove from inventory
    await db.delete(inv_item)
    
    # Update stats
    await update_user_stats(db, user, 'earned', sell_price)
    
    # Add transaction
    await add_transaction(db, user.id, 'sell_item', sell_price, f"Sold {inv_item.item.name}")
    
    await db.commit()
    
    return {"status": "ok", "amount": sell_price}

async def action_list_market(user: User, data: dict, db: AsyncSession):
    """List item on market"""
    uid = data.get('uid')
    price = data.get('price')
    
    result = await db.execute(
        select(InventoryItem)
        .where(and_(InventoryItem.uid == uid, InventoryItem.user_id == user.id))
    )
    inv_item = result.scalar_one_or_none()
    
    if not inv_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Create market listing
    listing = MarketListing(
        seller_id=user.id,
        item_id=inv_item.item_id,
        rarity=inv_item.rarity,
        price=price
    )
    db.add(listing)
    
    # Remove from inventory
    await db.delete(inv_item)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_buy_market(user: User, data: dict, db: AsyncSession):
    """Buy item from market"""
    listing_uid = data.get('listing_uid')
    
    result = await db.execute(
        select(MarketListing)
        .options(selectinload(MarketListing.seller))
        .where(and_(MarketListing.uid == listing_uid, MarketListing.status == 'active'))
    )
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot buy your own item")
    
    if user.balance < listing.price:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Transfer balance
    user.balance -= listing.price
    listing.seller.balance += listing.price
    
    # Add to buyer's inventory
    inv_item = InventoryItem(
        user_id=user.id,
        item_id=listing.item_id,
        rarity=listing.rarity
    )
    db.add(inv_item)
    
    # Update listing status
    listing.status = 'sold'
    
    # Update stats
    await update_user_stats(db, user, 'market_sales', 1)
    
    # Add transactions
    await add_transaction(db, user.id, 'buy_market', -listing.price, f"Bought item")
    await add_transaction(db, listing.seller_id, 'sell_market', listing.price, f"Sold item")
    
    await db.commit()
    
    return {"status": "ok"}

async def action_cancel_listing(user: User, data: dict, db: AsyncSession):
    """Cancel market listing"""
    listing_uid = data.get('listing_uid')
    
    result = await db.execute(
        select(MarketListing)
        .where(and_(MarketListing.uid == listing_uid, MarketListing.seller_id == user.id, MarketListing.status == 'active'))
    )
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Return to inventory
    inv_item = InventoryItem(
        user_id=user.id,
        item_id=listing.item_id,
        rarity=listing.rarity
    )
    db.add(inv_item)
    
    # Update listing status
    listing.status = 'cancelled'
    
    await db.commit()
    
    return {"status": "ok"}

async def action_send_chat(user: User, data: dict, db: AsyncSession):
    """Send chat message"""
    text = data.get('text')
    is_private = data.get('is_private', False)
    
    if not text or len(text) > 500:
        raise HTTPException(status_code=400, detail="Invalid message")
    
    message = ChatMessage(
        sender_id=user.id,
        server=user.server,
        text=text,
        is_private=is_private
    )
    db.add(message)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_craft(user: User, data: dict, db: AsyncSession):
    """Craft item"""
    recipe_id = data.get('recipe_id')
    
    # Get recipe
    result = await db.execute(
        select(CraftRecipe).where(CraftRecipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()
    
    if not recipe:
        return {"status": "error", "message": "Recipe not found"}
    
    # Check if user has required items
    for rarity, count in recipe.cost.items():
        result = await db.execute(
            select(func.count(InventoryItem.uid)).where(
                and_(InventoryItem.user_id == user.id, InventoryItem.rarity == rarity)
            )
        )
        user_count = result.scalar()
        
        if user_count < count:
            return {"status": "error", "message": f"Insufficient {rarity} items"}
    
    # Remove required items
    for rarity, count in recipe.cost.items():
        result = await db.execute(
            select(InventoryItem).where(
                and_(InventoryItem.user_id == user.id, InventoryItem.rarity == rarity)
            ).limit(count)
        )
        items_to_remove = result.scalars().all()
        for item in items_to_remove:
            await db.delete(item)
    
    # Get random item of result rarity
    items_result = await db.execute(
        select(Item).where(Item.rarity == recipe.result_rarity)
    )
    items = items_result.scalars().all()
    
    if not items:
        return {"status": "error", "message": "No items of this rarity"}
    
    item = random.choice(items)
    
    # Add to inventory
    inv_item = InventoryItem(
        user_id=user.id,
        item_id=item.id,
        rarity=item.rarity
    )
    db.add(inv_item)
    
    await db.commit()
    await db.refresh(inv_item)
    
    return {
        "status": "ok",
        "item": {
            "id": item.id,
            "name": item.name,
            "icon": item.icon,
            "rarity": item.rarity
        }
    }

async def action_buy_subscription(user: User, data: dict, db: AsyncSession):
    """Buy subscription"""
    plan = data.get('plan')
    
    prices = {'vip': 299, 'premium': 499}
    if plan not in prices:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    price = prices[plan]
    
    if user.balance < price:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user.balance -= price
    
    # Create subscription
    end_date = datetime.utcnow() + timedelta(days=30)
    subscription = Subscription(
        user_id=user.id,
        plan=plan,
        end_date=end_date
    )
    db.add(subscription)
    
    await add_transaction(db, user.id, 'buy_subscription', -price, f"Subscribed to {plan}")
    
    await db.commit()
    
    return {"status": "ok"}

async def action_send_gift(user: User, data: dict, db: AsyncSession):
    """Send gift to another user"""
    recipient_nick = data.get('recipient')
    amount = data.get('amount')
    
    if user.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Find recipient
    result = await db.execute(
        select(User).where(User.nickname == recipient_nick)
    )
    recipient = result.scalar_one_or_none()
    
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    if recipient.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot send to yourself")
    
    # Transfer
    user.balance -= amount
    recipient.balance += amount
    
    gift = Gift(
        sender_id=user.id,
        recipient_id=recipient.id,
        amount=amount
    )
    db.add(gift)
    
    await add_transaction(db, user.id, 'send_gift', -amount, f"Gift to {recipient_nick}")
    await add_transaction(db, recipient.id, 'receive_gift', amount, f"Gift from {user.nickname}")
    
    await db.commit()
    
    return {"status": "ok"}

async def action_card_payment(user: User, data: dict, db: AsyncSession):
    """Initiate card payment (mock)"""
    amount = data.get('amount')
    
    # Mock payment URL
    payment_url = f"https://payment.example.com/pay?amount={amount}&user_id={user.id}"
    
    return {"status": "ok", "payment_url": payment_url}

async def action_place_bid(user: User, data: dict, db: AsyncSession):
    """Place bid on auction"""
    auction_id = data.get('auction_id')
    amount = data.get('amount')
    
    result = await db.execute(
        select(Auction).where(and_(Auction.id == auction_id, Auction.status == 'active'))
    )
    auction = result.scalar_one_or_none()
    
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    if amount <= auction.current_bid:
        raise HTTPException(status_code=400, detail="Bid must be higher than current bid")
    
    if user.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Refund previous bidder
    if auction.current_bidder_id:
        result = await db.execute(select(User).where(User.id == auction.current_bidder_id))
        prev_bidder = result.scalar_one_or_none()
        if prev_bidder:
            prev_bidder.balance += auction.current_bid
    
    # Deduct from new bidder
    user.balance -= amount
    
    # Update auction
    auction.current_bid = amount
    auction.current_bidder_id = user.id
    
    # Record bid
    bid = Bid(
        auction_id=auction_id,
        user_id=user.id,
        amount=amount
    )
    db.add(bid)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_send_private_message(user: User, data: dict, db: AsyncSession):
    """Send private message"""
    dialog_id = data.get('dialog_id')
    text = data.get('text')
    
    result = await db.execute(
        select(Dialog).where(Dialog.id == dialog_id)
    )
    dialog = result.scalar_one_or_none()
    
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")
    
    if dialog.user1_id != user.id and dialog.user2_id != user.id:
        raise HTTPException(status_code=403, detail="Not in this dialog")
    
    message = PrivateMessage(
        dialog_id=dialog_id,
        sender_id=user.id,
        text=text
    )
    db.add(message)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_toggle_sound(user: User, db: AsyncSession):
    """Toggle sound setting"""
    user.sound_enabled = not user.sound_enabled
    await db.commit()
    return {"status": "ok"}

async def action_toggle_notifications(user: User, db: AsyncSession):
    """Toggle notifications setting"""
    user.notifications_enabled = not user.notifications_enabled
    await db.commit()
    return {"status": "ok"}

async def action_toggle_vibration(user: User, db: AsyncSession):
    """Toggle vibration setting"""
    user.vibration_enabled = not user.vibration_enabled
    await db.commit()
    return {"status": "ok"}

async def action_claim_daily(user: User, db: AsyncSession):
    """Claim daily reward"""
    if not user.daily_reward:
        user.daily_reward = DailyReward(user_id=user.id)
    
    last_claimed = user.daily_reward.last_claimed_date
    today = datetime.utcnow().date()
    
    if last_claimed and last_claimed.date() == today:
        raise HTTPException(status_code=400, detail="Already claimed today")
    
    # Calculate streak
    if last_claimed and (last_claimed.date() == today - timedelta(days=1)):
        user.daily_reward.streak += 1
    else:
        user.daily_reward.streak = 1
    
    # Calculate reward
    reward = 100 * user.daily_reward.streak
    user.balance += reward
    user.daily_reward.last_claimed_date = datetime.utcnow()
    
    await add_transaction(db, user.id, 'daily_reward', reward, f"Daily reward (streak {user.daily_reward.streak})")
    
    await db.commit()
    
    return {"status": "ok", "reward": reward, "streak": user.daily_reward.streak}

async def action_claim_quest(user: User, data: dict, db: AsyncSession):
    """Claim quest reward"""
    quest_id = data.get('quest_id')
    
    result = await db.execute(
        select(UserQuest).where(
            and_(UserQuest.user_id == user.id, UserQuest.quest_id == quest_id)
        )
    )
    user_quest = result.scalar_one_or_none()
    
    if not user_quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    if not user_quest.completed:
        raise HTTPException(status_code=400, detail="Quest not completed")
    
    if user_quest.claimed:
        raise HTTPException(status_code=400, detail="Already claimed")
    
    user_quest.claimed = True
    user.balance += user_quest.quest.reward
    
    await add_transaction(db, user.id, 'quest_reward', user_quest.quest.reward, f"Quest: {user_quest.quest.name}")
    
    await db.commit()
    
    return {"status": "ok", "reward": user_quest.quest.reward}

async def action_spin_wheel(user: User, db: AsyncSession):
    """Spin wheel of fortune"""
    cost = 50
    
    if user.balance < cost:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user.balance -= cost
    
    # Get prizes
    result = await db.execute(
        select(WheelPrize).where(WheelPrize.is_active == True)
    )
    prizes = result.scalars().all()
    
    if not prizes:
        # Default prizes
        prizes = [
            WheelPrize(name="Nothing", probability=0.5, reward_type="nothing", reward_amount=0),
            WheelPrize(name="100 coins", probability=0.3, reward_type="coins", reward_amount=100),
            WheelPrize(name="500 coins", probability=0.15, reward_type="coins", reward_amount=500),
            WheelPrize(name="1000 coins", probability=0.05, reward_type="coins", reward_amount=1000),
        ]
    
    # Select prize
    rand = random.random()
    cumulative = 0.0
    selected_prize = prizes[0]
    
    for prize in prizes:
        cumulative += prize.probability
        if rand <= cumulative:
            selected_prize = prize
            break
    
    # Award prize
    if selected_prize.reward_type == 'coins':
        user.balance += selected_prize.reward_amount
        await add_transaction(db, user.id, 'wheel_win', selected_prize.reward_amount, f"Wheel: {selected_prize.name}")
    
    # Record history
    history = WheelSpinHistory(
        user_id=user.id,
        prize_id=selected_prize.id if hasattr(selected_prize, 'id') else None
    )
    db.add(history)
    
    await db.commit()
    
    return {
        "status": "ok",
        "prize": {
            "name": selected_prize.name,
            "reward_type": selected_prize.reward_type,
            "reward_amount": selected_prize.reward_amount
        }
    }

async def action_spin_slots(user: User, data: dict, db: AsyncSession):
    """Spin slots"""
    cost = data.get('cost', 25)
    
    if user.balance < cost:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user.balance -= cost
    
    symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
    results = [random.choice(symbols) for _ in range(3)]
    
    win_amount = 0
    
    # Check for wins
    if results[0] == results[1] == results[2]:
        # Three of a kind
        if results[0] == '💎':
            win_amount = cost * 50
        elif results[0] == '7️⃣':
            win_amount = cost * 20
        else:
            win_amount = cost * 10
    elif results[0] == results[1] or results[1] == results[2]:
        # Two of a kind
        win_amount = cost * 2
    
    if win_amount > 0:
        user.balance += win_amount
        await add_transaction(db, user.id, 'slots_win', win_amount, f"Slots: {' '.join(results)}")
    
    # Record spin
    spin = SlotSpin(
        user_id=user.id,
        symbols=results,
        win_amount=win_amount
    )
    db.add(spin)
    
    await db.commit()
    
    return {
        "status": "ok",
        "symbols": results,
        "win_amount": win_amount
    }

async def action_start_pvp(user: User, data: dict, db: AsyncSession):
    """Start PvP match (mock)"""
    stake = data.get('stake', 100)
    
    if user.balance < stake:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Mock PvP - just return a random result
    won = random.choice([True, False])
    
    if won:
        user.balance += stake
        await update_user_stats(db, user, 'pvp_wins')
        await add_transaction(db, user.id, 'pvp_win', stake, "PvP match won")
    else:
        user.balance -= stake
        await add_transaction(db, user.id, 'pvp_loss', -stake, "PvP match lost")
    
    await db.commit()
    
    return {"status": "ok", "won": won, "stake": stake}

async def action_create_clan(user: User, data: dict, db: AsyncSession):
    """Create clan"""
    name = data.get('name')
    description = data.get('description', '')
    
    # Check if name exists
    result = await db.execute(select(Clan).where(Clan.name == name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Clan name already exists")
    
    clan = Clan(
        name=name,
        leader_id=user.id,
        description=description
    )
    db.add(clan)
    await db.flush()
    
    # Add leader as member
    member = ClanMember(
        clan_id=clan.id,
        user_id=user.id,
        role='leader'
    )
    db.add(member)
    
    await db.commit()
    
    return {"status": "ok", "clan_id": clan.id}

async def action_join_clan(user: User, data: dict, db: AsyncSession):
    """Join clan"""
    clan_id = data.get('clan_id')
    
    result = await db.execute(select(Clan).where(Clan.id == clan_id))
    clan = result.scalar_one_or_none()
    
    if not clan:
        raise HTTPException(status_code=404, detail="Clan not found")
    
    # Check if already member
    result = await db.execute(
        select(ClanMember).where(
            and_(ClanMember.clan_id == clan_id, ClanMember.user_id == user.id)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already a member")
    
    member = ClanMember(
        clan_id=clan_id,
        user_id=user.id,
        role='member'
    )
    db.add(member)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_equip_skin(user: User, data: dict, db: AsyncSession):
    """Equip skin"""
    skin_id = data.get('skin_id')
    
    # Check if user owns skin
    result = await db.execute(
        select(UserSkin).where(
            and_(UserSkin.user_id == user.id, UserSkin.skin_id == skin_id)
        )
    )
    user_skin = result.scalar_one_or_none()
    
    if not user_skin:
        raise HTTPException(status_code=404, detail="Skin not owned")
    
    # Unequip all other skins
    result = await db.execute(
        select(UserSkin).where(UserSkin.user_id == user.id)
    )
    all_skins = result.scalars().all()
    for skin in all_skins:
        skin.equipped = False
    
    # Equip selected skin
    user_skin.equipped = True
    
    await db.commit()
    
    return {"status": "ok"}

async def action_activate_promo(user: User, data: dict, db: AsyncSession):
    """Activate promo code"""
    code = data.get('code')
    
    result = await db.execute(
        select(PromoCode).where(
            and_(PromoCode.code == code, PromoCode.is_active == True)
        )
    )
    promo = result.scalar_one_or_none()
    
    if not promo:
        raise HTTPException(status_code=404, detail="Invalid promo code")
    
    if promo.uses_left <= 0:
        raise HTTPException(status_code=400, detail="Promo code expired")
    
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Promo code expired")
    
    # Award reward
    if promo.reward_type == 'coins':
        user.balance += promo.reward_amount
        await add_transaction(db, user.id, 'promo_code', promo.reward_amount, f"Promo: {code}")
    
    # Decrease uses
    promo.uses_left -= 1
    
    await db.commit()
    
    return {"status": "ok", "reward": promo.reward_amount}

async def action_submit_ticket(user: User, data: dict, db: AsyncSession):
    """Submit support ticket"""
    subject = data.get('subject')
    message = data.get('message')
    
    ticket = SupportTicket(
        user_id=user.id,
        subject=subject,
        message=message
    )
    db.add(ticket)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_admin_ban_user(user: User, data: dict, db: AsyncSession):
    """Admin: ban user"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not admin")
    
    target_id = data.get('user_id')
    reason = data.get('reason')
    
    # Create warning
    warning = UserWarning(
        user_id=target_id,
        admin_id=user.id,
        reason=reason
    )
    db.add(warning)
    
    # Log action
    log = AdminActionLog(
        admin_id=user.id,
        action="ban_user",
        details=f"Banned user {target_id}: {reason}"
    )
    db.add(log)
    
    await db.commit()
    
    return {"status": "ok"}

async def action_admin_broadcast(user: User, data: dict, db: AsyncSession):
    """Admin: send broadcast"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not admin")
    
    message = data.get('message')
    
    # Log action
    log = AdminActionLog(
        admin_id=user.id,
        action="broadcast",
        details=f"Broadcast: {message}"
    )
    db.add(log)
    
    await db.commit()
    
    return {"status": "ok"}

# ================= INITIALIZATION =================

@app.on_event("startup")
async def startup_event():
    """Initialize database and seed data"""
    await init_db()
    
    # Seed initial data
    async with AsyncSessionLocal() as db:
        # Check if servers exist
        result = await db.execute(select(Server))
        if result.first() is None:
            # Add default servers
            servers = [
                Server(server_name="Server 1", online=150, description="Основной сервер"),
                Server(server_name="Server 2", online=80, description="Альтернативный сервер"),
                Server(server_name="Server 3", online=200, description="VIP сервер"),
            ]
            for server in servers:
                db.add(server)

        # Check if cases exist
        result = await db.execute(select(Case))
        if result.first() is None:
            # Add default cases
            cases = [
                Case(
                    id="case_basic",
                    name="Базовый кейс",
                    icon="📦",
                    price=50,
                    chances={"common": 0.7, "rare": 0.25, "epic": 0.05}
                ),
                Case(
                    id="case_premium",
                    name="Премиум кейс",
                    icon="🎁",
                    price=200,
                    chances={"common": 0.4, "rare": 0.4, "epic": 0.15, "legendary": 0.05}
                ),
                Case(
                    id="case_legendary",
                    name="Легендарный кейс",
                    icon="👑",
                    price=1000,
                    chances={"rare": 0.3, "epic": 0.4, "legendary": 0.25, "mythic": 0.05}
                ),
            ]
            for case in cases:
                db.add(case)
        
        # Check if items exist
        result = await db.execute(select(Item))
        if result.first() is None:
            # Add default items
            items = [
                # Common
                Item(id="common_1", name="Железный меч", icon="⚔️", rarity="common", base_price=50),
                Item(id="common_2", name="Кожаная броня", icon="🛡️", rarity="common", base_price=50),
                Item(id="common_3", name="Зелье здоровья", icon="🧪", rarity="common", base_price=50),
                # Rare
                Item(id="rare_1", name="Стальной меч", icon="🗡️", rarity="rare", base_price=150),
                Item(id="rare_2", name="Кольчуга", icon="🥋", rarity="rare", base_price=150),
                Item(id="rare_3", name="Магический жезл", icon="🪄", rarity="rare", base_price=150),
                # Epic
                Item(id="epic_1", name="Огненный меч", icon="🔥", rarity="epic", base_price=400),
                Item(id="epic_2", name="Ледяная броня", icon="❄️", rarity="epic", base_price=400),
                Item(id="epic_3", name="Амулет силы", icon="💎", rarity="epic", base_price=400),
                # Legendary
                Item(id="legendary_1", name="Экскалибур", icon="⚡", rarity="legendary", base_price=1000),
                Item(id="legendary_2", name="Корона короля", icon="👑", rarity="legendary", base_price=1000),
                # Mythic
                Item(id="mythic_1", name="Божественный клинок", icon="🌟", rarity="mythic", base_price=3000),
            ]
            for item in items:
                db.add(item)

        # Check if craft recipes exist
        result = await db.execute(select(CraftRecipe))
        if result.first() is None:
            recipes = [
                CraftRecipe(
                    id="craft_rare",
                    name="Крафт: Редкий предмет",
                    result_rarity="rare",
                    cost={"common": 5},
                    description="5 обычных → 1 редкий"
                ),
                CraftRecipe(
                    id="craft_epic",
                    name="Крафт: Эпический предмет",
                    result_rarity="epic",
                    cost={"rare": 3},
                    description="3 редких → 1 эпический"
                ),
                CraftRecipe(
                    id="craft_legendary",
                    name="Крафт: Легендарный предмет",
                    result_rarity="legendary",
                    cost={"epic": 3},
                    description="3 эпических → 1 легендарный"
                ),
                CraftRecipe(
                    id="craft_mythic",
                    name="Крафт: Мифический предмет",
                    result_rarity="mythic",
                    cost={"legendary": 3},
                    description="3 легендарных → 1 мифический"
                ),
            ]
            for recipe in recipes:
                db.add(recipe)

        # Check if quests exist
        result = await db.execute(select(Quest))
        if result.first() is None:
            quests = [
                Quest(id="quest_open_10", name="Открой 10 кейсов", description="Открой 10 любых кейсов", reward=500, type="open_cases", target=10),
                Quest(id="quest_open_50", name="Открой 50 кейсов", description="Открой 50 любых кейсов", reward=3000, type="open_cases", target=50),
                Quest(id="quest_chat_10", name="Напиши 10 сообщений", description="Отправь 10 сообщений в чат", reward=200, type="chat_messages", target=10),
            ]
            for quest in quests:
                db.add(quest)
        
        # Check if achievements exist
        result = await db.execute(select(Achievement))
        if result.first() is None:
            achievements = [
                Achievement(id="ach_first_case", name="Первый кейс", description="Открой первый кейс", icon="🎁", reward=100, criteria_type="opened_cases", criteria_value=1),
                Achievement(id="ach_100_cases", name="Коллекционер", description="Открой 100 кейсов", icon="📦", reward=1000, criteria_type="opened_cases", criteria_value=100),
                Achievement(id="ach_rich", name="Богатый", description="Накопи 10000 монет", icon="💰", reward=500, criteria_type="balance", criteria_value=10000),
            ]
            for achievement in achievements:
                db.add(achievement)

        # Check if wheel prizes exist
        result = await db.execute(select(WheelPrize))
        if result.first() is None:
            prizes = [
                WheelPrize(name="Ничего", probability=0.5, reward_type="nothing", reward_amount=0),
                WheelPrize(name="100 монет", probability=0.3, reward_type="coins", reward_amount=100),
                WheelPrize(name="500 монет", probability=0.15, reward_type="coins", reward_amount=500),
                WheelPrize(name="1000 монет", probability=0.05, reward_type="coins", reward_amount=1000),
            ]
            for prize in prizes:
                db.add(prize)

        # Check if skins exist
        result = await db.execute(select(Skin))
        if result.first() is None:
            skins = [
                Skin(id="skin_default", name="Стандартный", icon="🎨", description="Стандартный скин", price=0),
                Skin(id="skin_gold", name="Золотой", icon="✨", description="Золотой скин", price=500),
                Skin(id="skin_diamond", name="Алмазный", icon="💠", description="Алмазный скин", price=1000),
            ]
            for skin in skins:
                db.add(skin)
        
        await db.commit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
