"""API эндпоинты для команд."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.domain.teams.service import TeamService
from app.schemas.team import CreateTeamRequest, TeamResponse

router = APIRouter(prefix="/team", tags=["Teams"])


@router.post("/add", response_model=TeamResponse, status_code=201)
async def create_team(
    request: CreateTeamRequest,
    session: AsyncSession = Depends(get_session),
):
    """Создать команду с участниками."""
    return await TeamService(session).create_team(
        request.team_name, [m.model_dump() for m in request.members]
    )


@router.get("/get")
async def get_team(
    team_name: str,
    session: AsyncSession = Depends(get_session),
):
    """Получить команду с участниками."""
    return await TeamService(session).get_team(team_name)
