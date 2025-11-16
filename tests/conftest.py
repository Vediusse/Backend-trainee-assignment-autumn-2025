"""Конфигурация тестов."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db.models import Team, User


@pytest.fixture(scope="function")
async def test_db():
    """Создать тестовую БД в памяти."""

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def session(test_db):
    """Создать сессию БД для теста."""
    async with test_db() as session:
        yield session


@pytest.fixture(scope="function")
async def mock_cache(monkeypatch):
    """Mock Redis кеш."""
    cache_dict = {}

    class MockRedis:
        async def get(self, key: str):
            return cache_dict.get(key)

        async def setex(self, key: str, ttl: int, value: str):
            cache_dict[key] = value

        async def delete(self, *keys):
            for key in keys:
                cache_dict.pop(key, None)

        async def keys(self, pattern: str):
            import fnmatch

            return [k for k in cache_dict.keys() if fnmatch.fnmatch(k, pattern)]

        async def close(self):
            pass

    mock_redis = MockRedis()
    monkeypatch.setattr("app.core.cache.redis_client", mock_redis)
    monkeypatch.setattr("app.core.cache.get_cache", lambda: mock_redis)
    return mock_redis


@pytest.fixture
async def sample_team(session):
    """Создать тестовую команду."""
    team = Team(team_name="backend")
    session.add(team)
    await session.flush()

    users = [
        User(user_id="u1", username="Alice", team_name="backend", is_active=True),
        User(user_id="u2", username="Bob", team_name="backend", is_active=True),
        User(user_id="u3", username="Charlie", team_name="backend", is_active=True),
        User(user_id="u4", username="Charlie", team_name="backend", is_active=True),
    ]
    for user in users:
        session.add(user)

    await session.commit()
    return team
