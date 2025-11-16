"""Репозиторий для работы с Pull Request'ами."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PullRequest, User, pr_reviewers
from app.db.repositories.base import BaseRepository


class PRRepository(BaseRepository[PullRequest]):
    """Репозиторий Pull Request'ов."""

    def __init__(self, session: AsyncSession):
        super().__init__(PullRequest, session)

    async def get_by_id(
        self, pr_id: str, load_author: bool = False, load_reviewers: bool = False
    ) -> PullRequest | None:
        """Получить PR по ID."""
        query = select(PullRequest).where(PullRequest.pull_request_id == pr_id)
        if load_author:
            query = query.options(selectinload(PullRequest.author))
        if load_reviewers:
            query = query.options(selectinload(PullRequest.reviewers))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists(self, pr_id: str) -> bool:
        """Проверить существование PR."""
        result = await self.session.execute(
            select(PullRequest.pull_request_id).where(PullRequest.pull_request_id == pr_id)
        )
        return result.scalar_one_or_none() is not None

    async def create_with_reviewers(
        self,
        pr_id: str,
        pr_name: str,
        author_id: str,
        reviewer_ids: list[str],
    ) -> PullRequest:
        """Создать PR с ревьюверами."""
        pr = PullRequest(
            pull_request_id=pr_id,
            pull_request_name=pr_name,
            author_id=author_id,
            status="OPEN",
            created_at=datetime.utcnow(),
        )
        self.session.add(pr)
        await self.session.flush()

        if reviewer_ids:
            from sqlalchemy import insert

            values = [{"pr_id": pr_id, "reviewer_id": reviewer_id} for reviewer_id in reviewer_ids]
            await self.session.execute(insert(pr_reviewers).values(values))
            await self.session.flush()

            await self.session.refresh(pr, ["reviewers"])

        return pr

    async def merge(self, pr_id: str) -> PullRequest | None:
        """Пометить PR как MERGED (идемпотентная операция)."""
        pr = await self.get_by_id(pr_id, load_author=True, load_reviewers=True)
        if not pr:
            return None

        if pr.status == "MERGED":
            return pr

        pr.status = "MERGED"
        pr.merged_at = datetime.utcnow()
        await self.session.flush()

        return pr

    async def reassign_reviewer(
        self, pr_id: str, old_reviewer_id: str, new_reviewer_id: str
    ) -> PullRequest | None:
        """Переназначить ревьювера."""
        pr = await self.get_by_id(pr_id, load_reviewers=True)
        if not pr:
            return None

        old_reviewer = next((r for r in pr.reviewers if r.user_id == old_reviewer_id), None)
        if not old_reviewer:
            return None

        new_reviewer = await self.session.execute(
            select(User).where(User.user_id == new_reviewer_id)
        )
        new_reviewer = new_reviewer.scalar_one_or_none()
        if not new_reviewer:
            return None

        pr.reviewers.remove(old_reviewer)
        pr.reviewers.append(new_reviewer)
        await self.session.flush()

        return pr

    async def get_all_open_prs_with_reviewers(self) -> list[PullRequest]:
        """Получить все открытые PR с ревьюверами."""
        query = (
            select(PullRequest)
            .where(PullRequest.status == "OPEN")
            .options(selectinload(PullRequest.reviewers))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(self) -> dict:
        """Получить статистику по PR."""
        from sqlalchemy import case, func

        stats_query = select(
            func.count(PullRequest.pull_request_id).label("total_prs"),
            func.sum(case((PullRequest.status == "OPEN", 1), else_=0)).label("open_prs"),
            func.sum(case((PullRequest.status == "MERGED", 1), else_=0)).label("merged_prs"),
        )
        result = await self.session.execute(stats_query)
        row = result.one()
        total_count = row.total_prs or 0
        open_count = row.open_prs or 0
        merged_count = row.merged_prs or 0

        pr_reviewer_counts = (
            select(
                PullRequest.pull_request_id,
                func.count(pr_reviewers.c.reviewer_id).label("reviewer_count"),
            )
            .outerjoin(pr_reviewers, PullRequest.pull_request_id == pr_reviewers.c.pr_id)
            .group_by(PullRequest.pull_request_id)
            .subquery()
        )

        count_query = select(
            func.sum(case((pr_reviewer_counts.c.reviewer_count == 0, 1), else_=0)).label("count_0"),
            func.sum(case((pr_reviewer_counts.c.reviewer_count == 1, 1), else_=0)).label("count_1"),
            func.sum(case((pr_reviewer_counts.c.reviewer_count == 2, 1), else_=0)).label("count_2"),
        ).select_from(pr_reviewer_counts)
        count_result = await self.session.execute(count_query)
        count_row = count_result.one()

        return {
            "total_prs": total_count,
            "open_prs": open_count,
            "merged_prs": merged_count,
            "prs_with_0_reviewers": int(count_row.count_0 or 0),
            "prs_with_1_reviewer": int(count_row.count_1 or 0),
            "prs_with_2_reviewers": int(count_row.count_2 or 0),
        }
