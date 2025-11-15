"""Сервис для работы с пользователями."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.repositories.user_repository import UserRepository
from app.domain.base_service import BaseService


class UserService(BaseService):
    """Сервис для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)

    async def set_is_active(self, user_id: str, is_active: bool) -> dict:
        """Установить флаг активности пользователя."""
        user = await self.user_repo.update_active(user_id, is_active)
        if not user:
            raise NotFoundException("User")

        cache_service = await self._get_cache_service()
        await cache_service.delete_pattern(f"users:get_reviews:{user_id}:*")

        return {
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "team_name": user.team_name,
                "is_active": user.is_active,
            }
        }

    async def get_reviews(self, user_id: str) -> dict:
        """Получить PR'ы, где пользователь назначен ревьювером."""
        cache_service = await self._get_cache_service()
        cache_key = f"users:get_reviews:{user_id}"

        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            return cached_result

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User")

        prs = await self.user_repo.get_review_prs(user_id)
        result = {
            "user_id": user_id,
            "pull_requests": [
                {
                    "pull_request_id": pr.pull_request_id,
                    "pull_request_name": pr.pull_request_name,
                    "author_id": pr.author_id,
                    "status": pr.status,
                }
                for pr in prs
            ],
        }

        await cache_service.set(cache_key, result, ttl=300)
        return result
