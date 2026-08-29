# config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8907615374:AAE9oS1KbtKtEuVCnNteDPQmg1ojGXaN2sk")

    # Admin Telegram ID
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "8601398572"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./storm_cases.db")

    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # WebApp URL
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "http://localhost:8000")

    # Crypto Pay (optional)
    CRYPTO_PAY_API_KEY: str = os.getenv("CRYPTO_PAY_API_KEY", "")

    # Payment Settings
    SELL_MULTIPLIER: float = float(os.getenv("SELL_MULTIPLIER", "0.5"))

    # Server Settings
    INITIAL_BALANCE: float = float(os.getenv("INITIAL_BALANCE", "100.0"))

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
