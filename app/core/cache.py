"""Настройка кеширования Redis."""

import json
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

redis_client: Optional[Redis] = None


async def init_cache():
    """
    Инициализация Redis.
    Попытается подключиться к Redis. В случае ошибки подключения,
    глобальный redis_client будет установлен в None, и кеширование будет пропущено.
    """
    global redis_client
    if redis_client is not None:
        return

    try:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

        await redis_client.ping()

    except ConnectionError:
        redis_client = None
    except Exception:
        redis_client = None


async def close_cache():
    """
    Закрытие соединения с Redis.
    Безопасно закрывает соединение, если оно существует, и обрабатывает возможные ошибки.
    """
    global redis_client
    if redis_client:
        try:
            await redis_client.close()

        except ConnectionError:
            pass
        finally:
            redis_client = None


async def get_cache() -> Optional[Redis]:
    """
    Получить клиент Redis.
    Если клиент еще не инициализирован, попытается его инициализировать.
    Возвращает клиент Redis или None, если Redis недоступен.
    """
    if redis_client is None:
        await init_cache()
    return redis_client


class CacheService:
    """
    Сервис для работы с кешем.
    Устойчив к сбоям Redis: операции с кешем будут пропущены,
    если Redis недоступен, без возникновения ошибок.
    """

    def __init__(self, redis_client_instance: Optional[Redis], ttl: int = settings.REDIS_TTL):
        self.redis = redis_client_instance
        self.ttl = ttl

        self._is_available = self.redis is not None

    @property
    def is_available(self) -> bool:
        """Возвращает текущий статус доступности кеша."""
        return self._is_available

    async def get(self, key: str) -> Optional[dict]:
        """
        Получить значение из кеша.
        В случае ошибки Redis или его недоступности, возвращает None.
        """
        if not self._is_available:
            return None
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except ConnectionError:

            self._is_available = False
        except Exception:

            self._is_available = False
        return None

    async def set(self, key: str, value: dict, ttl: Optional[int] = None):
        """
        Установить значение в кеш.
        В случае ошибки Redis или его недоступности, пропускает запись.
        """
        if not self._is_available:
            return
        try:
            ttl = ttl or self.ttl
            await self.redis.setex(key, ttl, json.dumps(value))
        except ConnectionError:

            self._is_available = False
        except Exception:

            self._is_available = False

    async def delete(self, key: str):
        """
        Удалить значение из кеша.
        В случае ошибки Redis или его недоступности, пропускает удаление.
        """
        if not self._is_available:
            return
        try:
            await self.redis.delete(key)
        except ConnectionError:

            self._is_available = False
        except Exception:

            self._is_available = False

    async def delete_pattern(self, pattern: str):
        """
        Удалить все ключи по паттерну.
        В случае ошибки Redis или его недоступности, пропускает удаление.
        """
        if not self._is_available:
            return
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except ConnectionError:
            self._is_available = False
        except Exception:
            self._is_available = False
