"""Foundation health contract tests."""

import sys
from types import TracebackType
from typing import cast

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.adapters.database import EXPECTED_ALEMBIC_HEAD
from evalgate.config import Settings
from evalgate.entrypoints import http
from evalgate.entrypoints.retrieval_runtime import database_event_loop


class _FakeEngine:
    def __init__(
        self,
        failure: Exception | None = None,
        *,
        migration_head: str = EXPECTED_ALEMBIC_HEAD,
        migration_failure: Exception | None = None,
    ) -> None:
        self.failure = failure
        self.migration_head = migration_head
        self.migration_failure = migration_failure
        self.executed = False
        self.disposed = False

    def connect(self) -> "_FakeConnectionContext":
        return _FakeConnectionContext(self)

    async def dispose(self) -> None:
        self.disposed = True


class _FakeConnectionContext:
    def __init__(self, engine: _FakeEngine) -> None:
        self.engine = engine

    async def __aenter__(self) -> "_FakeConnection":
        if self.engine.failure is not None:
            raise self.engine.failure
        return _FakeConnection(self.engine)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback


class _FakeConnection:
    def __init__(self, engine: _FakeEngine) -> None:
        self.engine = engine

    async def execute(self, statement: object) -> "_FakeResult":
        self.engine.executed = True
        if "alembic_version" in str(statement):
            if self.engine.migration_failure is not None:
                raise self.engine.migration_failure
            return _FakeResult((self.engine.migration_head,))
        return _FakeResult(())


class _FakeResult:
    def __init__(self, values: tuple[str, ...]) -> None:
        self.values = values

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> tuple[str, ...]:
        return self.values


def _settings() -> Settings:
    return Settings(
        database_url=SecretStr("postgresql+psycopg://ignored:ignored@localhost/ignored")
    )


def _app_with_engine(engine: _FakeEngine) -> FastAPI:
    return http.create_app(settings=_settings(), engine=cast(AsyncEngine, engine))


def test_liveness_has_stable_non_sensitive_contract() -> None:
    engine = _FakeEngine()

    with TestClient(_app_with_engine(engine)) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "service": "evalgate-api",
        "version": "0.3.1",
        "status": "alive",
        "checks": {},
    }
    assert "ignored" not in response.text
    assert engine.disposed


def test_readiness_success_executes_probe_and_disposes_engine() -> None:
    engine = _FakeEngine()

    with TestClient(_app_with_engine(engine)) as client:
        response = client.get("/health/ready")
        assert not engine.disposed

    assert response.status_code == 200
    assert response.json() == {
        "service": "evalgate-api",
        "version": "0.3.1",
        "status": "ready",
        "checks": {"database": "available", "migration": "current"},
    }
    assert engine.executed
    assert engine.disposed


def test_readiness_failure_is_non_sensitive_and_disposes_engine() -> None:
    engine = _FakeEngine(RuntimeError("database-url-marker"))

    with TestClient(_app_with_engine(engine)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "service": "evalgate-api",
        "version": "0.3.1",
        "status": "not_ready",
        "checks": {"database": "unavailable", "migration": "unknown"},
    }
    assert "database-url-marker" not in response.text
    assert engine.disposed


def test_readiness_rejects_migration_mismatch_without_exposing_head() -> None:
    engine = _FakeEngine(migration_head="unexpected-head")

    with TestClient(_app_with_engine(engine)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "database": "available",
        "migration": "mismatch",
    }
    assert "unexpected-head" not in response.text


def test_readiness_treats_missing_migration_table_as_mismatch() -> None:
    engine = _FakeEngine(migration_failure=RuntimeError("migration-table-marker"))

    with TestClient(_app_with_engine(engine)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "database": "available",
        "migration": "mismatch",
    }
    assert "migration-table-marker" not in response.text


@pytest.mark.parametrize(
    ("platform", "expected_loop"),
    [("win32", database_event_loop), ("linux", "auto")],
)
def test_main_disables_access_logging_and_selects_database_compatible_loop(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    expected_loop: object,
) -> None:
    invocation: dict[str, object] = {}

    def capture_run(app: str, **kwargs: object) -> None:
        invocation["app"] = app
        invocation.update(kwargs)

    monkeypatch.setattr(http, "get_settings", _settings)
    monkeypatch.setattr(uvicorn, "run", capture_run)
    monkeypatch.setattr(sys, "platform", platform)

    http.main()

    assert invocation["app"] == "evalgate.entrypoints.http:create_app"
    assert invocation["factory"] is True
    assert invocation["access_log"] is False
    assert invocation["loop"] == expected_loop
