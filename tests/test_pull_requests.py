"""Тесты для сервиса Pull Request'ов."""

import pytest

from app.core.exceptions import (
    PRExistsException,
    PRMergedException,
)
from app.domain.pull_requests.service import PullRequestService


@pytest.mark.asyncio
async def test_create_pr(session, mock_cache, sample_team):
    """Тест создания PR с автоматическим назначением ревьюверов."""
    service = PullRequestService(session)
    result = await service.create_pr("pr-1", "Test PR", "u1")
    assert result["pr"]["pull_request_id"] == "pr-1"
    assert result["pr"]["status"] == "OPEN"
    assert len(result["pr"]["assigned_reviewers"]) <= 2
    # Автор не должен быть в списке ревьюверов
    assert "u1" not in result["pr"]["assigned_reviewers"]


@pytest.mark.asyncio
async def test_create_pr_with_duplicate_id(session, mock_cache, sample_team):
    """Тест создания PR с дублирующимся ID."""
    service = PullRequestService(session)
    await service.create_pr("pr-1", "Test PR", "u1")

    with pytest.raises(PRExistsException):
        await service.create_pr("pr-1", "Another PR", "u2")


@pytest.mark.asyncio
async def test_merge_pr(session, mock_cache, sample_team):
    """Тест merge PR."""
    service = PullRequestService(session)
    await service.create_pr("pr-1", "Test PR", "u1")
    result = await service.merge_pr("pr-1")
    assert result["pr"]["status"] == "MERGED"
    assert result["pr"]["mergedAt"] is not None


@pytest.mark.asyncio
async def test_merge_pr_idempotent(session, mock_cache, sample_team):
    """Тест идемпотентности merge PR."""
    service = PullRequestService(session)
    await service.create_pr("pr-1", "Test PR", "u1")
    result1 = await service.merge_pr("pr-1")
    result2 = await service.merge_pr("pr-1")  # Повторный вызов
    assert result1["pr"]["status"] == "MERGED"
    assert result2["pr"]["status"] == "MERGED"
    assert result1["pr"]["mergedAt"] == result2["pr"]["mergedAt"]


@pytest.mark.asyncio
async def test_reassign_reviewer(session, mock_cache, sample_team):
    """Тест переназначения ревьювера."""
    service = PullRequestService(session)
    result = await service.create_pr("pr-1", "Test PR", "u1")
    old_reviewer = (
        result["pr"]["assigned_reviewers"][0] if result["pr"]["assigned_reviewers"] else None
    )

    if old_reviewer:
        reassign_result = await service.reassign_reviewer("pr-1", old_reviewer)
        assert "replaced_by" in reassign_result
        assert reassign_result["replaced_by"] != old_reviewer
        assert reassign_result["replaced_by"] in reassign_result["pr"]["assigned_reviewers"]


@pytest.mark.asyncio
async def test_reassign_on_merged_pr(session, mock_cache, sample_team):
    """Тест переназначения на merged PR."""
    service = PullRequestService(session)
    result = await service.create_pr("pr-1", "Test PR", "u1")
    old_reviewer = (
        result["pr"]["assigned_reviewers"][0] if result["pr"]["assigned_reviewers"] else None
    )

    if old_reviewer:
        await service.merge_pr("pr-1")
        with pytest.raises(PRMergedException):
            await service.reassign_reviewer("pr-1", old_reviewer)
