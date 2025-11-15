"""Сервис для работы со статистикой."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user_repository import UserRepository
from app.db.repositories.pr_repository import PRRepository
from app.domain.base_service import BaseService


class StatsService(BaseService):
    """Сервис для работы со статистикой."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.pr_repo = PRRepository(session)

    async def get_stats(self) -> dict:
        """Получить статистику по пользователям и PR."""
        cache_service = await self._get_cache_service()
        cache_key = "stats:get_stats"

        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            return cached_result

        user_stats_list = await self.user_repo.get_all_with_stats()
        pr_stats_dict = await self.pr_repo.get_stats()

        result = {
            "users": [
                {
                    "user_id": stat["user_id"],
                    "username": stat["username"],
                    "total_reviews": stat["total_reviews"],
                    "open_reviews": stat["open_reviews"],
                    "merged_reviews": stat["merged_reviews"],
                }
                for stat in user_stats_list
            ],
            "pull_requests": pr_stats_dict,
        }

        await cache_service.set(cache_key, result, ttl=300)
        return result
