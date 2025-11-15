"""Сервис для работы с пользователями."""

import random
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.models import PullRequest
from app.db.repositories.pr_repository import PRRepository
from app.db.repositories.user_repository import UserRepository
from app.domain.base_service import BaseService


class UserService(BaseService):
    """Сервис для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.pr_repo = PRRepository(session)

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

    async def bulk_deactivate_users(self, user_ids: List[str]) -> dict:

        if not user_ids:
            return {"deactivated_count": 0, "reassigned_prs_count": 0}

        users_before = await self.user_repo.get_users_by_ids(user_ids)
        deactivated_count = await self.user_repo.bulk_deactivate_by_ids(user_ids)

        cache = await self._get_cache_service()

        await cache.delete_pattern("users:get_reviews:*")

        # кеши по юзерам
        for uid in user_ids:
            await cache.delete(f"user:{uid}")
            await cache.delete(f"users:get_reviews:{uid}")

        # кеши по командам
        teams = {u.team_name for u in users_before if u.team_name}
        for team in teams:
            await cache.delete_pattern(f"teams:get_team:{team}:*")

        reassigned_count = await self._reassign_pull_requests(user_ids)

        return {
            "deactivated_count": deactivated_count,
            "reassigned_prs_count": reassigned_count,
        }

    async def _reassign_pull_requests(self, user_ids: List[str]) -> int:
        prs = await self.user_repo.get_prs_by_reviewer_ids(user_ids)
        reassigned_count = 0

        for pr in prs:
            reviewers_to_replace = [
                r for r in pr.reviewers if r.user_id in user_ids and not r.is_active
            ]
            if not reviewers_to_replace:
                continue

            current_ids = [r.user_id for r in pr.reviewers]

            for old in reviewers_to_replace:
                reassigned = await self._reassign_single_reviewer(pr, old, current_ids)
                reassigned_count += reassigned

        return reassigned_count

    async def _reassign_single_reviewer(self, pr: PullRequest, old_reviewer, current_ids) -> int:
        candidates = await self.user_repo.get_active_candidates_for_pr(
            excluded_user_ids=[old_reviewer.user_id],
            current_pr_reviewers_ids=current_ids,
            limit=10,
        )

        if candidates:
            new = random.choice(candidates)
            await self.pr_repo.reassign_reviewer(
                pr.pull_request_id, old_reviewer.user_id, new.user_id
            )
            return 1


        try:
            pr.reviewers.remove(old_reviewer)
        except ValueError:
            pass

        await self.session.flush()
        return 0
