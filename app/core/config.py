"""Конфигурация приложения."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/pr_reviewer"
    DATABASE_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL: int = 300
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    DEBUG: bool = False

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
