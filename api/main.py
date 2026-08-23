"""FastAPI composition root for the Nexora AI HTTP adapter."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import perf_counter
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from api.config import APISettings
from api.errors import APIError
from api.routers.dashboard import router as dashboard_router
from api.routers.backlinks import router as backlinks_router
from api.routers.seo import router as seo_router
from api.routers.settings import router as settings_router
from api.routers.rank_tracking import router as rank_tracking_router
from api.routers.site_crawl import router as site_crawl_router
from api.routers.competitor_gap import router as competitor_gap_router
from api.routers.content import router as content_router
from api.routers.aeo_geo import router as aeo_geo_router
from api.routers.ai_visibility import router as ai_visibility_router
from api.routers.outreach import router as outreach_router
from api.routers.local_seo import router as local_seo_router
from api.routers.analytics import router as analytics_router
from api.routers.ads import router as ads_router
from api.routers.workspaces import router as workspaces_router
from api.routers.system import router as system_router
from src.core.constants import APP_NAME, APP_VERSION
from src.core.exceptions import NexoraError

logger = logging.getLogger("nexora.api")


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", "unknown"),
            }
        },
    )


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Construct an isolated application instance for production or tests."""

    resolved_settings = settings or APISettings.from_environment()
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        resolved_settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Nexora API lifecycle started")
        try:
            yield
        finally:
            logger.info("Nexora API lifecycle stopped")

    application = FastAPI(
        title=f"{APP_NAME} API",
        version=APP_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid4())
        request.state.request_id = request_id[:128]
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception as error:
            logger.exception("Unexpected API failure", exc_info=error, extra={"request_id": request.state.request_id})
            response = _error_response(
                request,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
            )
        duration_ms = (perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        logger.info(
            "API request completed",
            extra={
                "request_id": request.state.request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="The request is invalid.",
        )

    @application.exception_handler(APIError)
    async def api_error(request: Request, error: APIError) -> JSONResponse:
        return _error_response(request, status_code=error.status_code, code=error.code, message=error.message)

    @application.exception_handler(NexoraError)
    async def nexora_error(request: Request, error: NexoraError) -> JSONResponse:
        logger.warning("Nexora request failed", extra={"request_id": request.state.request_id})
        return _error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=error.__class__.__name__,
            message=str(error) or "The request could not be completed.",
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        code = "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR"
        return _error_response(
            request,
            status_code=error.status_code,
            code=code,
            message="The requested resource was not found." if error.status_code == 404 else "The request could not be completed.",
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception(
            "Unexpected API failure",
            exc_info=error,
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
        )

    application.include_router(system_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(seo_router, prefix="/api/v1")
    application.include_router(backlinks_router, prefix="/api/v1")
    application.include_router(settings_router, prefix="/api/v1")
    application.include_router(workspaces_router, prefix="/api/v1")
    application.include_router(rank_tracking_router, prefix="/api/v1")
    application.include_router(site_crawl_router, prefix="/api/v1")
    application.include_router(competitor_gap_router, prefix="/api/v1")
    application.include_router(content_router, prefix="/api/v1")
    application.include_router(aeo_geo_router, prefix="/api/v1")
    application.include_router(ai_visibility_router, prefix="/api/v1")
    application.include_router(outreach_router, prefix="/api/v1")
    application.include_router(local_seo_router, prefix="/api/v1")
    application.include_router(analytics_router, prefix="/api/v1")
    application.include_router(ads_router, prefix="/api/v1")
    return application


app = create_app()
