"""Схемы для команд."""

from pydantic import BaseModel, ConfigDict


class TeamMemberSchema(BaseModel):
    """Схема участника команды."""

    user_id: str
    username: str
    is_active: bool


class TeamSchema(BaseModel):
    """Схема команды."""

    team_name: str
    members: list[TeamMemberSchema]

    model_config = ConfigDict(from_attributes=True)


class TeamResponse(BaseModel):
    """Ответ с командой."""

    team: TeamSchema


class CreateTeamRequest(BaseModel):
    """Запрос на создание команды."""

    team_name: str
    members: list[TeamMemberSchema]
