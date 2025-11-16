"""Сервис для работы с командами."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, TeamExistsException
from app.db.models import Team, User
from app.db.repositories.team_repository import TeamRepository
from app.db.repositories.user_repository import UserRepository
from app.domain.base_service import BaseService
from app.schemas.team import TeamMemberSchema


class TeamService(BaseService):
    """Сервис для работы с командами."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.team_repo = TeamRepository(session)
        self.user_repo = UserRepository(session)

    async def create_team(self, team_name: str, members: list[dict]) -> dict:
        """Создать команду с участниками."""
        cache_service = await self._get_cache_service()
        await cache_service.delete_pattern(f"teams:get_team:{team_name}:*")

        if await self.team_repo.exists(team_name):
            raise TeamExistsException()

        team = Team(team_name=team_name)
        self.session.add(team)
        await self.session.flush()

        for member_data in members:
            member = TeamMemberSchema(**member_data)
            await cache_service.delete(f"users:get_reviews:{member.user_id}")

            user = await self.user_repo.get_by_id(member.user_id)
            if user:
                user.username = member.username
                user.is_active = member.is_active
                user.team_name = team_name
            else:
                user = User(
                    user_id=member.user_id,
                    username=member.username,
                    team_name=team_name,
                    is_active=member.is_active,
                )
                self.session.add(user)

        await self.session.flush()

        team = await self.team_repo.get_by_name(team_name, load_members=True)
        team_data = self._team_to_schema(team)

        cache_key = f"teams:get_team:{team_name}:{json.dumps(sorted([('team_name', team_name)]), sort_keys=True)}"
        await cache_service.set(cache_key, team_data)

        return {"team": team_data}

    async def get_team(self, team_name: str) -> dict:
        """Получить команду с участниками."""
        cache_service = await self._get_cache_service()
        cache_key = f"teams:get_team:{team_name}:{json.dumps(sorted([('team_name', team_name)]), sort_keys=True)}"

        cached_result = await cache_service.get(cache_key)
        if cached_result is not None:
            return {"team": cached_result}

        team = await self.team_repo.get_by_name(team_name, load_members=True)
        if not team:
            raise NotFoundException("Team")

        team_data = self._team_to_schema(team)
        await cache_service.set(cache_key, team_data)

        return {"team": team_data}

    def _team_to_schema(self, team: Team) -> dict:
        """Преобразовать модель в схему."""
        return {
            "team_name": team.team_name,
            "members": [
                {
                    "user_id": member.user_id,
                    "username": member.username,
                    "is_active": member.is_active,
                }
                for member in team.members
            ],
        }
