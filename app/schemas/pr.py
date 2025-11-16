"""Схемы для Pull Request'ов."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PullRequestSchema(BaseModel):
    """Схема Pull Request."""

    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: str
    assigned_reviewers: list[str] = Field(default_factory=list, max_length=2)
    createdAt: datetime | None = None
    mergedAt: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PullRequestShortSchema(BaseModel):
    """Краткая схема Pull Request."""

    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class PullRequestResponse(BaseModel):
    """Ответ с Pull Request."""

    pr: PullRequestSchema


class CreatePRRequest(BaseModel):
    """Запрос на создание PR."""

    pull_request_id: str
    pull_request_name: str
    author_id: str


class MergePRRequest(BaseModel):
    """Запрос на merge PR."""

    pull_request_id: str


class ReassignRequest(BaseModel):
    """Запрос на переназначение ревьювера."""

    pull_request_id: str
    old_user_id: str


class ReassignResponse(BaseModel):
    """Ответ на переназначение."""

    pr: PullRequestSchema
    replaced_by: str
