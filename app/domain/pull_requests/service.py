"""Сервис для работы с Pull Request'ами."""

import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NoCandidateException,
    NotAssignedException,
    NotFoundException,
    PRExistsException,
    PRMergedException,
)
from app.db.repositories.pr_repository import PRRepository
from app.db.repositories.team_repository import TeamRepository
from app.db.repositories.user_repository import UserRepository
from app.domain.base_service import BaseService


class PullRequestService(BaseService):
    """Сервис для работы с Pull Request'ами."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.pr_repo = PRRepository(session)
        self.user_repo = UserRepository(session)
        self.team_repo = TeamRepository(session)

    async def create_pr(self, pr_id: str, pr_name: str, author_id: str) -> dict:
        """Создать PR и автоматически назначить ревьюверов."""

        if await self.pr_repo.exists(pr_id):
            raise PRExistsException()

        author = await self.user_repo.get_by_id(author_id)
        if not author:
            raise NotFoundException("Author")

        team = await self.team_repo.get_by_name(author.team_name)
        if not team:
            raise NotFoundException("Team")

        candidates = await self.user_repo.get_active_by_team(
            author.team_name, exclude_user_id=author_id, limit=2
        )
        random.shuffle(candidates)
        reviewer_ids = [user.user_id for user in candidates[:2]]

        await self.pr_repo.create_with_reviewers(pr_id, pr_name, author_id, reviewer_ids)
        await self.session.flush()

        cache_service = await self._get_cache_service()
        for reviewer_id in reviewer_ids:
            await cache_service.delete(f"users:get_reviews:{reviewer_id}")

        pr = await self.pr_repo.get_by_id(pr_id, load_reviewers=True)

        return {"pr": self._pr_to_schema(pr)}

    async def get_pr(self, pr_id: str) -> dict:
        """Получить PR по идентификатору."""
        pr = await self.pr_repo.get_by_id(pr_id, load_author=True, load_reviewers=True)

        if not pr:
            raise NotFoundException("PR")

        return {"pr": self._pr_to_schema(pr)}

    async def merge_pr(self, pr_id: str) -> dict:
        """Пометить PR как MERGED (идемпотентная операция)."""
        pr = await self.pr_repo.merge(pr_id)
        if not pr:
            raise NotFoundException("PR")

        return {"pr": self._pr_to_schema(pr)}

    async def reassign_reviewer(self, pr_id: str, old_user_id: str) -> dict:
        """Переназначить ревьювера."""
        pr = await self.pr_repo.get_by_id(pr_id, load_reviewers=True)
        if not pr:
            raise NotFoundException("PR")

        if pr.status == "MERGED":
            raise PRMergedException()

        old_reviewer_ids = [r.user_id for r in pr.reviewers]
        if old_user_id not in old_reviewer_ids:
            raise NotAssignedException()

        old_reviewer = await self.user_repo.get_by_id(old_user_id)
        if not old_reviewer:
            raise NotFoundException("User")

        team_name = old_reviewer.team_name

        candidates = await self.user_repo.get_active_by_team(
            team_name, exclude_user_id=old_user_id, limit=100
        )

        candidates = [u for u in candidates if u.user_id not in old_reviewer_ids]

        if not candidates:
            raise NoCandidateException()

        new_reviewer = random.choice(candidates)

        pr = await self.pr_repo.reassign_reviewer(pr_id, old_user_id, new_reviewer.user_id)
        if not pr:
            raise NotFoundException("PR")

        return {"pr": self._pr_to_schema(pr), "replaced_by": new_reviewer.user_id}

    def _pr_to_schema(self, pr) -> dict:
        """Преобразовать модель в схему."""
        reviewers = pr.reviewers if hasattr(pr, "reviewers") and pr.reviewers else []
        return {
            "pull_request_id": pr.pull_request_id,
            "pull_request_name": pr.pull_request_name,
            "author_id": pr.author_id,
            "status": pr.status,
            "assigned_reviewers": [r.user_id for r in reviewers],
            "createdAt": pr.created_at.isoformat() if pr.created_at else None,
            "mergedAt": pr.merged_at.isoformat() if pr.merged_at else None,
        }
