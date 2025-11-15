"""Схемы для статистики."""

from pydantic import BaseModel


class UserStatsSchema(BaseModel):
    """Статистика по пользователю."""

    user_id: str
    username: str
    total_reviews: int
    open_reviews: int
    merged_reviews: int


class PRStatsSchema(BaseModel):
    """Статистика по PR."""

    total_prs: int
    open_prs: int
    merged_prs: int
    prs_with_0_reviewers: int
    prs_with_1_reviewer: int
    prs_with_2_reviewers: int


class StatsResponse(BaseModel):
    """Ответ со статистикой."""

    users: list[UserStatsSchema]
    pull_requests: PRStatsSchema
