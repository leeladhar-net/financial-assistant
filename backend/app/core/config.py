from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Financial Intelligence Assistant"
    ENVIRONMENT: str = "development"
    DEMO_MODE: bool = True
    LOG_LEVEL: str = "INFO"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = "demo_bot_token"
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite:///./financial_assistant.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM / AI Config
    LLM_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"

    # Market Data
    FINNHUB_API_KEY: Optional[str] = None
    NEWSAPI_KEY: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        # Render provides postgres:// but SQLAlchemy requires postgresql://
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
