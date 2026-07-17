import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.admin import router as admin_router
from .api.attachments import router as attachments_router
from .api.builtin_connector_secrets import router as builtin_connector_secrets_router
from .api.channels import router as channels_router
from .api.generic_connectors import router as generic_connectors_router
from .api.generic_connectors import webhook_router
from .api.health import router as health_router
from .api.ingestion import router as ingestion_router
from .api.message_actions import router as message_actions_router
from .api.replies import router as replies_router
from .core.config import ALLINO_ALLOWED_ORIGINS, ALLINO_ENV
from .core import rate_limit
from .core.crypto import validate_encryption_configuration
from .core.security_headers import build_security_headers
from .db.session import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    validate_encryption_configuration()
    init_db()
    yield


def _docs_enabled_for_env(env: str) -> bool:
    """Publicly reachable in dev for convenience; the full route/schema map is
    recon value to an attacker in production, so it's turned off there --
    same "closed by default" posture as everything else under CLAUDE.md's
    security gate."""
    return env != "production"


_docs_enabled = _docs_enabled_for_env(ALLINO_ENV)
app = FastAPI(
    title="ALLinO Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

allowed_origins = [o.strip() for o in ALLINO_ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=[
        "Content-Type", "X-API-Key", "X-Tenant-Id", "Authorization", "Accept", "X-TOTP-Code",
    ],
)


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if rate_limit.ALLINO_RATE_LIMIT_ENABLED and rate_limit.is_rate_limited_path(request.url.path):
        allowed, retry_after = rate_limit.RATE_LIMITER.consume(
            key=rate_limit.rate_limit_key(request),
            limit=rate_limit.ALLINO_RATE_LIMIT_REQUESTS,
            window_seconds=rate_limit.ALLINO_RATE_LIMIT_WINDOW_SECONDS,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    for header_name, header_value in build_security_headers(request).items():
        response.headers[header_name] = header_value
    return response

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = str(uuid.uuid4())
    logger.exception("Unhandled exception (error_id=%s) on %s %s", error_id, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": error_id},
    )


app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(generic_connectors_router)
app.include_router(builtin_connector_secrets_router)
app.include_router(webhook_router)
app.include_router(replies_router)
app.include_router(message_actions_router)
app.include_router(admin_router)
app.include_router(attachments_router)
app.include_router(channels_router)
