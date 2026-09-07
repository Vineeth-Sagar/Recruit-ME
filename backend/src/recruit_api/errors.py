"""Domain errors and the JSON error envelope."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("recruit_api.errors")


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


def _envelope(status_code: int, code: str, message: str, extra: object = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if extra is not None:
        body["error"]["detail"] = extra
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # registered only for AppError
    return _envelope(exc.status_code, exc.code, exc.message)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _envelope(
        422,
        "validation_error",
        "the request body failed validation",
        extra=[{"loc": e.get("loc"), "msg": e.get("msg")} for e in exc.errors()],
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return _envelope(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "an unexpected error occurred"
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
