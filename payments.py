# payments.py
# ============================================================
# STORM CASES - Payment Integration
# ============================================================

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from config import settings
from models import User, TransactionHistory, Subscription


# ================= HELPER FUNCTIONS =================

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


# ================= TELEGRAM STARS PAYMENT =================

async def process_stars_payment(
        db: AsyncSession,
        user_id: int,
        stars_amount: int
) -> dict:
    """
    Process Telegram Stars payment
    Conversion rates:
    - 10 stars = 500 coins
    - 50 stars = 3000 coins
    - 100 stars = 10000 coins
    - 500 stars = 60000 coins
    """
    conversion_rates = {
        10: 500,
        50: 3000,
        100: 10000,
        500: 60000
    }

    coins = conversion_rates.get(stars_amount, 0)

    if coins == 0:
        return {"status": "error", "message": "Invalid stars amount"}

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Add coins
    user.balance += coins

    # Add transaction
    await add_transaction(
        db,
        user_id,
        'stars_payment',
        coins,
        f'Telegram Stars: {stars_amount} ⭐'
    )

    await db.commit()

    return {
        "status": "ok",
        "coins_added": coins,
        "stars_used": stars_amount
    }


# ================= CRYPTO PAYMENT =================

async def create_crypto_payment(
        db: AsyncSession,
        user_id: int,
        amount_rub: float
) -> dict:
    """
    Create crypto payment (USDT TRC20)
    Mock implementation - in production, integrate with Crypto Pay API
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Calculate coins (1 RUB = 10 coins)
    coins = amount_rub * 10

    # Mock payment address
    payment_address = f"TJ{user_id}MockAddress1234567890"

    # In production, you would:
    # 1. Create invoice via Crypto Pay API
    # 2. Get payment address
    # 3. Set up webhook to handle payment confirmation

    return {
        "status": "ok",
        "payment_address": payment_address,
        "amount_usdt": amount_rub / 90,  # Approximate rate
        "coins_to_receive": coins,
        "expires_in": 3600  # 1 hour
    }


async def confirm_crypto_payment(
        db: AsyncSession,
        user_id: int,
        transaction_hash: str,
        amount_rub: float
) -> dict:
    """
    Confirm crypto payment
    Mock implementation - verify transaction hash on blockchain
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Calculate coins
    coins = amount_rub * 10

    # Add coins
    user.balance += coins

    # Add transaction
    await add_transaction(
        db,
        user_id,
        'crypto_payment',
        coins,
        f'Crypto payment: {transaction_hash}'
    )

    await db.commit()

    return {
        "status": "ok",
        "coins_added": coins
    }


# ================= CARD PAYMENT =================

async def create_card_payment(
        db: AsyncSession,
        user_id: int,
        amount_rub: float
) -> dict:
    """
    Create card payment
    Mock implementation - integrate with payment gateway (YooKassa, UnitPay, etc.)
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Calculate coins
    coins = amount_rub * 10

    # Mock payment URL
    payment_url = f"https://payment.example.com/checkout?amount={amount_rub}&user_id={user_id}"

    # In production, you would:
    # 1. Create payment via payment gateway API
    # 2. Get payment URL/ID
    # 3. Set up webhook to handle payment confirmation

    return {
        "status": "ok",
        "payment_url": payment_url,
        "amount_rub": amount_rub,
        "coins_to_receive": coins,
        "payment_id": f"pay_{user_id}_{int(datetime.utcnow().timestamp())}"
    }


async def confirm_card_payment(
        db: AsyncSession,
        user_id: int,
        payment_id: str,
        amount_rub: float
) -> dict:
    """
    Confirm card payment
    Mock implementation - verify payment with payment gateway
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Calculate coins
    coins = amount_rub * 10

    # Add coins
    user.balance += coins

    # Add transaction
    await add_transaction(
        db,
        user_id,
        'card_payment',
        coins,
        f'Card payment: {payment_id}'
    )

    await db.commit()

    return {
        "status": "ok",
        "coins_added": coins
    }


# ================= SUBSCRIPTION PAYMENT =================

async def buy_subscription(
        db: AsyncSession,
        user_id: int,
        plan: str,
        payment_method: str = "stars"
) -> dict:
    """
    Buy subscription (VIP or Premium)
    """
    plans = {
        'vip': {'price': 299, 'duration_days': 30},
        'premium': {'price': 499, 'duration_days': 30}
    }

    if plan not in plans:
        return {"status": "error", "message": "Invalid plan"}

    plan_info = plans[plan]
    price = plan_info['price']

    # Get user
    result = await db.execute(
        select(User).options(selectinload(User.subscriptions)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Check balance
    if user.balance < price:
        return {"status": "error", "message": "Insufficient balance"}

    # Deduct balance
    user.balance -= price

    # Calculate end date
    end_date = datetime.utcnow() + timedelta(days=plan_info['duration_days'])

    # Create or update subscription
    existing_sub = None
    for sub in user.subscriptions:
        if sub.plan == plan and sub.active:
            existing_sub = sub
            break

    if existing_sub:
        # Extend existing subscription
        existing_sub.end_date = end_date
    else:
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            end_date=end_date,
            active=True
        )
        db.add(subscription)

    # Add transaction
    await add_transaction(
        db,
        user_id,
        'buy_subscription',
        -price,
        f'Subscription: {plan}'
    )

    await db.commit()

    return {
        "status": "ok",
        "plan": plan,
        "end_date": end_date.isoformat()
    }


# ================= PROMO CODES =================

async def activate_promo_code(
        db: AsyncSession,
        user_id: int,
        code: str
) -> dict:
    """
    Activate promo code
    """
    from models import PromoCode

    # Get promo code
    result = await db.execute(
        select(PromoCode).where(
            PromoCode.code == code,
            PromoCode.is_active == True
        )
    )
    promo = result.scalar_one_or_none()

    if not promo:
        return {"status": "error", "message": "Invalid promo code"}

    # Check uses
    if promo.uses_left <= 0:
        return {"status": "error", "message": "Promo code expired"}

    # Check expiration
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return {"status": "error", "message": "Promo code expired"}

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"status": "error", "message": "User not found"}

    # Award reward
    if promo.reward_type == 'coins':
        user.balance += promo.reward_amount
        await add_transaction(
            db,
            user_id,
            'promo_code',
            promo.reward_amount,
            f'Promo: {code}'
        )
    elif promo.reward_type == 'item':
        # Add item to inventory
        from models import InventoryItem
        inv_item = InventoryItem(
            user_id=user_id,
            item_id=promo.reward_item_id,
            rarity='common'  # Would need to look up actual rarity
        )
        db.add(inv_item)

    # Decrease uses
    promo.uses_left -= 1

    await db.commit()

    return {
        "status": "ok",
        "reward_type": promo.reward_type,
        "reward_amount": promo.reward_amount
    }


# ================= REFERRAL SYSTEM =================

async def process_referral(
        db: AsyncSession,
        referrer_id: int,
        referred_id: int
) -> dict:
    """
    Process referral bonus
    """
    from models import Referral, User

    # Check if referral already exists
    result = await db.execute(
        select(Referral).where(
            Referral.referred_id == referred_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return {"status": "error", "message": "Already referred"}

    # Get users
    result = await db.execute(select(User).where(User.id == referrer_id))
    referrer = result.scalar_one_or_none()

    result = await db.execute(select(User).where(User.id == referred_id))
    referred = result.scalar_one_or_none()

    if not referrer or not referred:
        return {"status": "error", "message": "User not found"}

    if referrer_id == referred_id:
        return {"status": "error", "message": "Cannot refer yourself"}

    # Calculate bonus (10% of initial balance)
    bonus = settings.INITIAL_BALANCE * 0.1

    # Add bonus to referrer
    referrer.balance += bonus

    # Create referral record
    referral = Referral(
        referrer_id=referrer_id,
        referred_id=referred_id,
        bonus_percent=10.0
    )
    db.add(referral)

    # Add transaction
    await add_transaction(
        db,
        referrer_id,
        'referral_bonus',
        bonus,
        f'Referral: {referred.nickname}'
    )

    await db.commit()

    return {
        "status": "ok",
        "bonus": bonus
    }
