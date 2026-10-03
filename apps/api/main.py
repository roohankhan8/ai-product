import logging
import re
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from core.config import get_settings
from core.errors import APIError
from core.logging import configure_logging
from core.request_context import request_id_context
from database import dispose_database
from exception_handlers import (
    api_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from routes.health import router as health_router

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        await dispose_database()


app = FastAPI(
    title="AI Operations API",
    description="Backend API for the AI Operations Platform.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(health_router)


@app.middleware("http")
async def add_request_context(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    incoming_id = request.headers.get("X-Request-ID", "")
    request_id = (
        incoming_id
        if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", incoming_id)
        else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    context_token = request_id_context.set(request_id)
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        return response
    finally:
        request_id_context.reset(context_token)
