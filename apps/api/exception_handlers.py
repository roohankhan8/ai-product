import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.errors import APIError
from core.request_context import request_id_context

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request_id_context.get()


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    **extra: Any,
) -> JSONResponse:
    request_id = _request_id(request)
    content: dict[str, Any] = {
        "error": {"code": code, "message": message},
        "request_id": request_id,
        **extra,
    }
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return _error_response(request, exc.status_code, exc.code, exc.message)


async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _error_response(request, exc.status_code, "http_error", message)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request,
        422,
        "validation_error",
        "Request validation failed",
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id(request)
    logger.error(
        "Unhandled API error",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"request_id": request_id},
    )
    return _error_response(
        request,
        500,
        "internal_error",
        "An unexpected error occurred",
    )
