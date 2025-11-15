"""Зависимости для API."""

from app.core.database import get_db


async def get_session():
    """Получить сессию БД."""
    async for session in get_db():
        yield session
