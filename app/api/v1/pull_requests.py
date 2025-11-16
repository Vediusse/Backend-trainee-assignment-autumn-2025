"""API эндпоинты для Pull Request'ов."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.domain.pull_requests.service import PullRequestService
from app.schemas.pr import (
    CreatePRRequest,
    MergePRRequest,
    PullRequestResponse,
    ReassignRequest,
    ReassignResponse,
)

router = APIRouter(prefix="/pullRequest", tags=["PullRequests"])


@router.post("/create", response_model=PullRequestResponse, status_code=201)
async def create_pr(
    request: CreatePRRequest,
    session: AsyncSession = Depends(get_session),
):
    """Создать PR и автоматически назначить до 2 ревьюверов из команды автора."""
    return await PullRequestService(session).create_pr(
        request.pull_request_id, request.pull_request_name, request.author_id
    )


@router.post("/merge", response_model=PullRequestResponse)
async def merge_pr(
    request: MergePRRequest,
    session: AsyncSession = Depends(get_session),
):
    """Пометить PR как MERGED (идемпотентная операция)."""
    return await PullRequestService(session).merge_pr(request.pull_request_id)


@router.post("/reassign", response_model=ReassignResponse)
async def reassign_reviewer(
    request: ReassignRequest,
    session: AsyncSession = Depends(get_session),
):
    """Переназначить конкретного ревьювера на другого из его команды."""
    return await PullRequestService(session).reassign_reviewer(
        request.pull_request_id, request.old_user_id
    )


@router.get("")
async def get_pr(
    pr_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Получить PR по идентификатору."""
    return await PullRequestService(session).get_pr(pr_id)
