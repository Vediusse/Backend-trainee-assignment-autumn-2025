"""Базовый класс для сервисов."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheService, get_cache


class BaseService:
    """Базовый класс для всех сервисов."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_cache_service(self) -> CacheService:
        """Получить сервис кеширования."""
        redis_client = await get_cache()
        return CacheService(redis_client)
