"""Интеграционные тесты E2E."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_e2e_pr_workflow(session, mock_cache):
    """E2E тест полного цикла работы с PR."""
    from app.api.dependencies import get_session

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        team_response = await client.post(
            "/team/add",
            json={
                "team_name": "backend-mck",
                "members": [
                    {"user_id": "u1", "username": "Alice", "is_active": True},
                    {"user_id": "u2", "username": "Bob", "is_active": True},
                    {"user_id": "u3", "username": "Charlie", "is_active": True},
                ],
            },
        )
        assert team_response.status_code == 201

        pr_response = await client.post(
            "/pullRequest/create",
            json={
                "pull_request_id": "pr-1-mck",
                "pull_request_name": "Add feature",
                "author_id": "u1",
            },
        )
        assert pr_response.status_code == 201
        pr_data = pr_response.json()["pr"]
        assert pr_data["status"] == "OPEN"
        assert len(pr_data["assigned_reviewers"]) <= 2
        assert "u1" not in pr_data["assigned_reviewers"]

        reviews_response = await client.get("/users/getReview", params={"user_id": "u2"})
        assert reviews_response.status_code == 200
        reviews_data = reviews_response.json()
        assert reviews_data["user_id"] == "u2"

        if pr_data["assigned_reviewers"]:
            old_reviewer = pr_data["assigned_reviewers"][0]
            reassign_response = await client.post(
                "/pullRequest/reassign",
                json={"pull_request_id": "pr-1-mck", "old_user_id": old_reviewer},
            )
            assert reassign_response.status_code == 200
            reassign_data = reassign_response.json()
            assert "replaced_by" in reassign_data
            assert reassign_data["replaced_by"] != old_reviewer

        merge_response = await client.post(
            "/pullRequest/merge", json={"pull_request_id": "pr-1-mck"}
        )
        assert merge_response.status_code == 200
        merge_data = merge_response.json()["pr"]
        assert merge_data["status"] == "MERGED"
        assert merge_data["mergedAt"] is not None

        if pr_data["assigned_reviewers"]:
            reassign_after_merge = await client.post(
                "/pullRequest/reassign",
                json={
                    "pull_request_id": "pr-1-mck",
                    "old_user_id": pr_data["assigned_reviewers"][0],
                },
            )
            assert reassign_after_merge.status_code == 409

        stats_response = await client.get("/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "users" in stats_data
        assert "pull_requests" in stats_data
        assert stats_data["pull_requests"]["total_prs"] >= 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_e2e_stats(session, mock_cache):
    """E2E тест статистики."""
    from app.api.dependencies import get_session

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Создаем данные
        await client.post(
            "/team/add",
            json={
                "team_name": "qa",
                "members": [
                    {"user_id": "u7", "username": "Grace", "is_active": True},
                    {"user_id": "u8", "username": "Henry", "is_active": True},
                ],
            },
        )

        await client.post(
            "/pullRequest/create",
            json={
                "pull_request_id": "pr-3",
                "pull_request_name": "Test PR",
                "author_id": "u7",
            },
        )

        stats_response = await client.get("/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()

        assert "users" in stats
        assert "pull_requests" in stats
        assert isinstance(stats["users"], list)
        assert isinstance(stats["pull_requests"], dict)

        pr_stats = stats["pull_requests"]
        assert "total_prs" in pr_stats
        assert "open_prs" in pr_stats
        assert "merged_prs" in pr_stats
        assert pr_stats["total_prs"] >= 1

        user_stats = {u["user_id"]: u for u in stats["users"]}
        assert "u7" in user_stats or "u8" in user_stats

    app.dependency_overrides.clear()
