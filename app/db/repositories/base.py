"""Базовый репозиторий."""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий для работы с БД."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: str) -> ModelType | None:
        """Получить по ID (переопределяется в дочерних классах)."""
        raise NotImplementedError("Subclasses must implement get_by_id")

    async def get_all(self, limit: int | None = None, offset: int = 0) -> list[ModelType]:
        """Получить все записи."""
        query = select(self.model).offset(offset)
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """Создать запись."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType, **kwargs) -> ModelType:
        """Обновить запись."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType):
        """Удалить запись."""
        await self.session.delete(instance)
        await self.session.flush()
