"""API эндпоинты для пользователей."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.domain.users.service import UserService
from app.schemas.user import (
    BulkDeactivateResponse,
    GetReviewsResponse,
    SetIsActiveRequest,
    UserDeactivationRequest,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/setIsActive", response_model=UserResponse)
async def set_is_active(
    request: SetIsActiveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Установить флаг активности пользователя."""
    return await UserService(session).set_is_active(request.user_id, request.is_active)


@router.get("/getReview", response_model=GetReviewsResponse)
async def get_reviews(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Получить PR'ы, где пользователь назначен ревьювером."""
    return await UserService(session).get_reviews(user_id)


@router.post("/bulkDeactivate", response_model=BulkDeactivateResponse)
async def bulk_deactivate(
    request: UserDeactivationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Массово деактивировать пользователей команды и переназначить открытые PR."""
    return BulkDeactivateResponse(
        **(await UserService(session).bulk_deactivate_users(request.user_ids))
    )
