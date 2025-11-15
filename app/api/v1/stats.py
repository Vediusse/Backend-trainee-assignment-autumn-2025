"""API эндпоинты для статистики."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.domain.stats.service import StatsService
from app.schemas.stats import StatsResponse

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    """Получить статистику по пользователям и PR."""
    return StatsResponse(**(await StatsService(session).get_stats()))
