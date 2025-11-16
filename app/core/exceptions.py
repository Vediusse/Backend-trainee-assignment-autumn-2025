"""Обработка исключений."""

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ServiceException(HTTPException):
    """Базовое исключение сервиса."""

    def __init__(
        self, error_code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(status_code=http_status, detail={"code": error_code, "message": message})


class TeamExistsException(ServiceException):
    """Команда уже существует."""

    def __init__(self):
        super().__init__("TEAM_EXISTS", "team_name already exists", status.HTTP_400_BAD_REQUEST)


class NotFoundException(ServiceException):
    """Ресурс не найден."""

    def __init__(self, resource: str = "resource"):
        super().__init__("NOT_FOUND", f"{resource} not found", status.HTTP_404_NOT_FOUND)


class PRExistsException(ServiceException):
    """PR уже существует."""

    def __init__(self):
        super().__init__("PR_EXISTS", "PR id already exists", status.HTTP_409_CONFLICT)


class PRMergedException(ServiceException):
    """PR уже в статусе MERGED."""

    def __init__(self):
        super().__init__("PR_MERGED", "cannot reassign on merged PR", status.HTTP_409_CONFLICT)


class NotAssignedException(ServiceException):
    """Ревьювер не назначен на PR."""

    def __init__(self):
        super().__init__(
            "NOT_ASSIGNED", "reviewer is not assigned to this PR", status.HTTP_409_CONFLICT
        )


class NoCandidateException(ServiceException):
    """Нет доступных кандидатов для переназначения."""

    def __init__(self):
        super().__init__(
            "NO_CANDIDATE", "no active replacement candidate in team", status.HTTP_409_CONFLICT
        )


async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
    """Обработчик исключений сервиса."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Обработчик HTTP исключений."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": exc.detail}},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Обработчик ошибок валидации."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation error",
                "details": exc.errors(),
            }
        },
    )
