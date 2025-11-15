"""SQLAlchemy модели базы данных."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

pr_reviewers = Table(
    "pr_reviewers",
    Base.metadata,
    Column(
        "pr_id",
        String,
        ForeignKey("pull_requests.pull_request_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "reviewer_id", String, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    ),
    Index("idx_pr_reviewers_reviewer", "reviewer_id"),
)


class Team(Base):
    """Модель команды."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("team_name", name="uq_teams_team_name"),
        {"comment": "Команды"},
    )

    team_name = Column(String(255), primary_key=True, nullable=False, comment="Название команды")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Дата создания")

    members = relationship("User", back_populates="team", cascade="all, delete-orphan")


class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_users_user_id"),
        Index("idx_users_team_active", "team_name", "is_active"),
        {"comment": "Пользователи"},
    )

    user_id = Column(String(255), primary_key=True, nullable=False, comment="ID пользователя")
    username = Column(String(255), nullable=False, comment="Имя пользователя")
    team_name = Column(
        String(255),
        ForeignKey("teams.team_name", ondelete="CASCADE"),
        nullable=False,
        comment="Название команды",
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="Флаг активности")

    team = relationship("Team", back_populates="members")
    authored_prs = relationship(
        "PullRequest", back_populates="author", foreign_keys="PullRequest.author_id"
    )
    reviewed_prs = relationship("PullRequest", secondary=pr_reviewers, back_populates="reviewers")


class PullRequest(Base):
    """Модель Pull Request."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("pull_request_id", name="uq_pull_requests_pr_id"),
        Index("idx_pr_author", "author_id"),
        {"comment": "Pull Request'ы"},
    )

    pull_request_id = Column(String(255), primary_key=True, nullable=False, comment="ID PR")
    pull_request_name = Column(String(500), nullable=False, comment="Название PR")
    author_id = Column(
        String(255),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="ID автора",
    )
    status = Column(String(20), default="OPEN", nullable=False, comment="Статус: OPEN или MERGED")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Дата создания")
    merged_at = Column(DateTime, nullable=True, comment="Дата merge")

    author = relationship("User", back_populates="authored_prs", foreign_keys=[author_id])
    reviewers = relationship("User", secondary=pr_reviewers, back_populates="reviewed_prs")
