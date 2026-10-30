"""Application settings using pydantic-settings"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Core
    APP_NAME: str = "SocialPilot AI"
    DEBUG: bool = True

    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "socialpilot")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./dev.db"
    )
    # Synchronous DB URL for migration tools (fallback to SQLite)
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "sqlite:///./dev.db"
    )

    # Redis / Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"

    # AI Provider
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Instagram (mock mode)
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_OAUTH_REDIRECT_URI: str = os.getenv(
        "META_OAUTH_REDIRECT_URI", "http://localhost:3000/api/auth/callback"
    )
    MOCK_INSTAGRAM: bool = not (META_APP_ID and META_APP_SECRET)

    # Object storage (MinIO for dev)
    OBJECT_STORAGE_ENDPOINT: str = os.getenv("OBJECT_STORAGE_ENDPOINT", "http://localhost:9000")
    OBJECT_STORAGE_BUCKET: str = os.getenv("OBJECT_STORAGE_BUCKET", "media")
    OBJECT_STORAGE_ACCESS_KEY: str = os.getenv("OBJECT_STORAGE_ACCESS_KEY", "minioadmin")
    OBJECT_STORAGE_SECRET_KEY: str = os.getenv("OBJECT_STORAGE_SECRET_KEY", "minioadmin")

    # Mode flag – True = use mocks for OpenAI & Meta; False = use real APIs
    # Defaults to True when neither OPENAI_API_KEY nor META creds are set.
    # Override explicitly with USE_MOCK=false in .env to force real mode.
    USE_MOCK: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-derive USE_MOCK from credential presence unless explicitly set
        import os
        if os.getenv("USE_MOCK") is None:
            self.USE_MOCK = not bool(self.OPENAI_API_KEY)

settings = Settings()
