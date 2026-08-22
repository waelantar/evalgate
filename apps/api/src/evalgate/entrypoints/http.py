"""FastAPI application factory and foundation health endpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal, cast

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from evalgate import __version__
from evalgate.adapters.database import check_database_readiness
from evalgate.config import Settings, get_settings


class HealthResponse(BaseModel):
    """Stable health response without sensitive configuration."""

    model_config = ConfigDict(extra="forbid")

    service: Literal["evalgate-api"]
    version: str
    status: Literal["alive", "ready", "not_ready"]
    checks: dict[str, str]


def _build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def create_app(settings: Settings | None = None, engine: AsyncEngine | None = None) -> FastAPI:
    """Build an application instance with explicit, testable dependencies."""

    resolved_settings = settings or get_settings()
    resolved_engine = engine or _build_engine(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await resolved_engine.dispose()

    app = FastAPI(
        title="EvalGate Foundation API",
        version=__version__,
        description=(
            "Health-only contract. Product endpoints are not implemented by the foundation."
        ),
        lifespan=lifespan,
    )
    app.state.database_engine = resolved_engine

    @app.get(
        "/health/live",
        response_model=HealthResponse,
        operation_id="getLiveness",
        response_description="Process is alive.",
        tags=["health"],
    )
    async def liveness() -> HealthResponse:
        return HealthResponse(
            service="evalgate-api",
            version=__version__,
            status="alive",
            checks={},
        )

    @app.get(
        "/health/ready",
        response_model=HealthResponse,
        operation_id="getReadiness",
        response_description="Required foundation dependencies are available.",
        responses={
            503: {
                "model": HealthResponse,
                "description": "A required foundation dependency is unavailable.",
            }
        },
        tags=["health"],
    )
    async def readiness(request: Request) -> HealthResponse | JSONResponse:
        database_engine = cast(AsyncEngine, request.app.state.database_engine)
        state = await check_database_readiness(database_engine)
        payload = HealthResponse(
            service="evalgate-api",
            version=__version__,
            status="ready" if state.ready else "not_ready",
            checks={"database": state.database, "migration": state.migration},
        )
        if not state.ready:
            return JSONResponse(status_code=503, content=payload.model_dump())
        return payload

    return app


def main() -> None:
    """Run the local API without exposing it beyond loopback by default."""

    settings = get_settings()
    uvicorn.run(
        "evalgate.entrypoints.http:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )
