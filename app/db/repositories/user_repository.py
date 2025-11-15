"""Репозиторий для работы с пользователями."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update

from app.db.models import PullRequest, pr_reviewers
from sqlalchemy import func, case
from app.db.models import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий пользователей."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_id(self, user_id: str, load_team: bool = False) -> Optional[User]:
        """Получить пользователя по ID."""
        query = select(User).where(User.user_id == user_id)
        if load_team:
            query = query.options(selectinload(User.team))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_by_team(
        self, team_name: str, exclude_user_id: Optional[str] = None, limit: int = 2
    ) -> List[User]:
        """Получить активных пользователей команды, исключая указанного."""
        query = select(User).where(
            User.team_name == team_name,
            User.is_active == True,  # noqa: E712
        )
        if exclude_user_id:
            query = query.where(User.user_id != exclude_user_id)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_active(self, user_id: str, is_active: bool) -> Optional[User]:
        """Обновить флаг активности."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = is_active
            await self.session.flush()
        return user

    async def get_review_prs(self, user_id: str) -> List:
        """Получить PR'ы, где пользователь ревьювер."""
        from app.db.models import PullRequest, pr_reviewers

        query = (
            select(PullRequest)
            .join(pr_reviewers, PullRequest.pull_request_id == pr_reviewers.c.pr_id)
            .where(pr_reviewers.c.reviewer_id == user_id)
            .order_by(PullRequest.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def bulk_deactivate_by_team(self, team_name: str) -> int:
        """Массово деактивировать пользователей команды."""
        result = await self.session.execute(
            update(User)
            .where(User.team_name == team_name, User.is_active == True)  # noqa: E712
            .values(is_active=False)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return result.rowcount or 0

    async def get_all_with_stats(self) -> List[dict]:
        """Получить всех пользователей со статистикой ревью."""

        review_stats = (
            select(
                pr_reviewers.c.reviewer_id,
                func.count(pr_reviewers.c.pr_id).label("total_reviews"),
                func.sum(case((PullRequest.status == "OPEN", 1), else_=0)).label("open_reviews"),
            )
            .join(PullRequest, pr_reviewers.c.pr_id == PullRequest.pull_request_id)
            .group_by(pr_reviewers.c.reviewer_id)
            .subquery()
        )

        query = (
            select(
                User.user_id,
                User.username,
                func.coalesce(review_stats.c.total_reviews, 0).label("total_reviews"),
                func.coalesce(review_stats.c.open_reviews, 0).label("open_reviews"),
            )
            .outerjoin(review_stats, User.user_id == review_stats.c.reviewer_id)
            .order_by(User.user_id)
        )

        result = await self.session.execute(query)
        return [
            {
                "user_id": row.user_id,
                "username": row.username,
                "total_reviews": int(row.total_reviews or 0),
                "open_reviews": int(row.open_reviews or 0),
                "merged_reviews": int((row.total_reviews or 0) - (row.open_reviews or 0)),
            }
            for row in result.all()
        ]
