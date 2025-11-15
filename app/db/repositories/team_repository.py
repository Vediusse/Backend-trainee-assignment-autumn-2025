"""Репозиторий для работы с командами."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Team
from app.db.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Репозиторий команд."""

    def __init__(self, session: AsyncSession):
        super().__init__(Team, session)

    async def get_by_name(self, team_name: str, load_members: bool = True) -> Optional[Team]:
        """Получить команду по имени."""
        query = select(Team).where(Team.team_name == team_name)
        if load_members:
            query = query.options(selectinload(Team.members))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists(self, team_name: str) -> bool:
        """Проверить существование команды."""
        result = await self.session.execute(
            select(Team.team_name).where(Team.team_name == team_name)
        )
        return result.scalar_one_or_none() is not None
