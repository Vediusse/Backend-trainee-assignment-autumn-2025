"""Тесты для сервиса команд."""

import pytest

from app.core.exceptions import NotFoundException, TeamExistsException
from app.domain.teams.service import TeamService


@pytest.mark.asyncio
async def test_create_team(session, mock_cache):
    """Тест создания команды."""
    service = TeamService(session)
    members = [
        {"user_id": "u1", "username": "Alice", "is_active": True},
        {"user_id": "u2", "username": "Bob", "is_active": True},
    ]
    result = await service.create_team("backend", members)
    assert "team" in result
    assert result["team"]["team_name"] == "backend"
    assert len(result["team"]["members"]) == 2


@pytest.mark.asyncio
async def test_create_duplicate_team(session, mock_cache):
    """Тест создания дублирующейся команды."""
    service = TeamService(session)
    members = [{"user_id": "u1", "username": "Alice", "is_active": True}]
    await service.create_team("backend", members)

    with pytest.raises(TeamExistsException):
        await service.create_team("backend", members)


@pytest.mark.asyncio
async def test_get_team(session, mock_cache, sample_team):
    """Тест получения команды."""
    service = TeamService(session)
    result = await service.get_team("backend")
    assert result["team"]["team_name"] == "backend"
    assert len(result["team"]["members"]) == 4


@pytest.mark.asyncio
async def test_get_nonexistent_team(session, mock_cache):
    """Тест получения несуществующей команды."""
    service = TeamService(session)
    with pytest.raises(NotFoundException):
        await service.get_team("nonexistent")
