"""Operational endpoints with no external-provider side effects."""

from __future__ import annotations

import sqlite3
import asyncio
from contextlib import closing

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from api.config import APISettings
from api.schemas.system import SystemStatus, VersionResponse
from src.core.constants import APP_NAME, APP_VERSION

router = APIRouter(tags=["system"])


@router.get("/health", response_model=SystemStatus)
async def health() -> SystemStatus:
    return SystemStatus(status="ok", service=APP_NAME, version=APP_VERSION)


@router.get(
    "/ready",
    response_model=SystemStatus,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": SystemStatus}},
)
async def readiness(request: Request) -> SystemStatus | JSONResponse:
    settings: APISettings = request.app.state.settings
    try:
        def probe() -> None:
            settings.database_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(settings.database_path, timeout=2.0)) as connection:
                connection.execute("SELECT 1").fetchone()
        await asyncio.to_thread(probe)
    except (OSError, sqlite3.Error):
        payload = SystemStatus(
            status="not_ready", service=APP_NAME, version=APP_VERSION
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )
    return SystemStatus(status="ready", service=APP_NAME, version=APP_VERSION)


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(service=APP_NAME, version=APP_VERSION)
