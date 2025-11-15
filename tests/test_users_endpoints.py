"""Тесты для сервиса пользователей."""

import pytest

from app.core.exceptions import NotFoundException
from app.domain.users.service import UserService


@pytest.mark.asyncio
async def test_set_user_active(session, mock_cache, sample_team):
    """Тест установки флага активности пользователя."""
    service = UserService(session)
    result = await service.set_is_active("u1", False)
    assert result["user"]["is_active"] is False


@pytest.mark.asyncio
async def test_set_nonexistent_user_active(session, mock_cache):
    """Тест установки флага активности несуществующего пользователя."""
    service = UserService(session)
    with pytest.raises(NotFoundException):
        await service.set_is_active("nonexistent", False)


@pytest.mark.asyncio
async def test_get_reviews(session, mock_cache, sample_team):
    """Тест получения PR'ов пользователя."""
    from app.domain.pull_requests.service import PullRequestService

    pr_service = PullRequestService(session)
    await pr_service.create_pr("pr-1", "Test PR", "u1")

    user_service = UserService(session)
    result = await user_service.get_reviews("u2")
    assert "pull_requests" in result
    # u2 может быть назначен ревьювером
    assert isinstance(result["pull_requests"], list)