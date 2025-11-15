"""Схемы для пользователей."""

from typing import List

from pydantic import BaseModel, ConfigDict
from app.schemas.pr import PullRequestShortSchema


class UserSchema(BaseModel):
    """Схема пользователя."""

    user_id: str
    username: str
    team_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Ответ с пользователем."""

    user: UserSchema


class SetIsActiveRequest(BaseModel):
    """Запрос на установку флага активности."""

    user_id: str
    is_active: bool


class BulkDeactivateRequest(BaseModel):
    """Запрос на массовую деактивацию пользователей команды."""

    team_name: str


class BulkDeactivateResponse(BaseModel):
    """Ответ на массовую деактивацию."""

    deactivated_count: int
    reassigned_prs_count: int


class GetReviewsResponse(BaseModel):
    """Ответ со списком PR'ов пользователя."""

    user_id: str
    pull_requests: list["PullRequestShortSchema"]

    model_config = ConfigDict(from_attributes=True)


class UserDeactivationRequest(BaseModel):  # Переименовал для ясности
    """Схема для деактивации пользователей по списку ID."""

    user_ids: List[str]


UserResponse.model_rebuild()
GetReviewsResponse.model_rebuild()
