from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BASE_URL: str
    JWT_SECRET_KEY: Optional[str | None] = None
    JWT_ALGORITHM: Optional[str | None] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = None
    REFRESH_TOKEN_EXPIRE_DAYS: Optional[int] = None

    REDIS_URL: Optional[str | None] = None
    CELERY_BROKER_URL: Optional[str | None] = None
    CELERY_RESULT_BACKEND: Optional[str | None] = None

    SMTP_HOST: Optional[str | None] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str | None] = None
    SMTP_PASSWORD: Optional[str | None] = None
    EMAILS_FROM_NAME: Optional[str | None] = None
    EMAILS_FROM_EMAIL: Optional[str | None] = None

    OTP_TTL_SECONDS: int = 900
    OTP_RESEND_COOLDOWN_SECONDS: int = 120


    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
