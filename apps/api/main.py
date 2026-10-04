import logging
import re
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from core.config import get_settings
from core.errors import APIError
from core.logging import configure_logging
from core.rate_limit import allow_request
from core.request_context import request_id_context
from database import dispose_database
from exception_handlers import (
    api_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from routes.auth import router as auth_router
from routes.approvals import router as approvals_router
from routes.chat import router as chat_router
from routes.documents import router as documents_router
from routes.health import router as health_router
from routes.tenant import router as tenant_router

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(tenant_router)


@app.middleware("http")
async def add_request_context(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    limits = {
        "/auth/dev-login": (10, 300),
        "/api/v1/chat": (60, 60),
        "/api/v1/documents/upload": (20, 300),
        "/api/v1/approvals": (60, 60),
    }
    matched = next((item for path, item in limits.items() if request.url.path == path), None)
    if matched:
        client = request.client.host if request.client else "unknown"
        if not await allow_request(f"{client}:{request.url.path}", *matched):
            return Response(
                content='{"error":{"code":"rate_limited","message":"Too many requests"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(matched[1])},
            )
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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
