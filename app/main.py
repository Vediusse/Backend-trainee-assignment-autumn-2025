"""Главный модуль FastAPI приложения."""

from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI
from pathlib import Path

from app.api.v1 import stats
from app.api.v1 import health, pull_requests, teams, users
from app.core.database import close_db, init_db
from app.core.exceptions import (
    http_exception_handler,
    service_exception_handler,
    validation_exception_handler,
    ServiceException,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="PR Reviewer Assignment Service",
    version="1.0.0",
    lifespan=lifespan,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_path = Path(__file__).parent.parent / "openapi.yml"
    with open(openapi_path, "r", encoding="utf-8") as f:
        openapi_schema = yaml.load(f, Loader=yaml.BaseLoader)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Регистрируем обработчики исключений
app.add_exception_handler(ServiceException, service_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Регистрируем роутеры
app.include_router(health.router)
app.include_router(teams.router)
app.include_router(users.router)
app.include_router(pull_requests.router)
app.include_router(stats.router)


if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
