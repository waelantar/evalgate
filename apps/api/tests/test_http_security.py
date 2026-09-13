"""EG-013A adversarial HTTP boundary and public route integration tests."""

from __future__ import annotations

from asyncio import sleep
from collections.abc import Iterator
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    ProviderConfigurationError,
)
from evalgate.application.search import SearchEmbeddingPort, SearchRepositoryPort
from evalgate.config import Settings
from evalgate.entrypoints.http import create_app


class _Engine:
    async def dispose(self) -> None:
        return None


def _public_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "public",
        "database_url": SecretStr("postgresql+psycopg://ignored/ignored"),
        "embedding_mode": EmbeddingMode.REFERENCE,
        "generation_mode": GenerationMode.DISABLED,
        "reference_embedding_snapshot": "ignored",
        "allowed_origins": "https://demo.example",
        "rate_identity_secret": SecretStr("s" * 32),
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _client(
    *, client_address: tuple[str, int] = ("testclient", 50_000), **settings: object
) -> TestClient:
    app = create_app(
        settings=_public_settings(**settings),
        engine=cast(AsyncEngine, _Engine()),
        search_repository=cast(SearchRepositoryPort, object()),
        search_embedding=cast(SearchEmbeddingPort, object()),
    )
    return TestClient(app, raise_server_exceptions=False, client=client_address)


def test_public_mode_exposes_health_but_hides_docs_and_mutation_shapes() -> None:
    with _client() as client:
        live = client.get("/health/live")
        docs = client.get("/openapi.json")
        mutation = client.post("/api/v1/evaluation-runs/import", json={})

    assert live.status_code == 200
    assert docs.status_code == 404
    assert mutation.status_code == 404
    assert mutation.json()["code"] == "route.unavailable"


def test_direct_public_app_construction_rejects_fixture_provider_bypass() -> None:
    with pytest.raises(ProviderConfigurationError):
        create_app(
            settings=Settings(
                environment="public",
                allowed_origins="https://demo.example",
                rate_identity_secret=SecretStr("s" * 32),
            ),
            engine=cast(AsyncEngine, _Engine()),
        )


def test_security_headers_are_present_on_success_and_rejection() -> None:
    with _client() as client:
        responses = [client.get("/health/live"), client.get("/openapi.json")]

    for response in responses:
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["strict-transport-security"].startswith("max-age=")
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_exact_origin_cors_allows_configured_origin_and_denies_another() -> None:
    with _client() as client:
        accepted = client.options(
            "/api/v1/search",
            headers={
                "Origin": "https://demo.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        rejected = client.options(
            "/api/v1/search",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert accepted.status_code == 200
    assert accepted.headers["access-control-allow-origin"] == "https://demo.example"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers


def test_oversized_body_is_rejected_without_echo_or_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "private-question-marker"
    body = '{"question":"' + marker + ("x" * 2000) + '"}'
    with _client(request_body_limit_bytes=1024) as client, caplog.at_level("DEBUG"):
        response = client.post(
            "/api/v1/ask", content=body, headers={"content-type": "application/json"}
        )

    assert response.status_code == 413
    assert response.json()["code"] == "request.too_large"
    assert marker not in response.text
    assert marker not in caplog.text


def test_chunked_body_without_content_length_is_stopped_at_streaming_limit() -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"question":"'
        yield b"x" * 700
        yield b"y" * 700
        yield b'"}'

    with _client(request_body_limit_bytes=1024) as client:
        response = client.post(
            "/api/v1/ask",
            content=chunks(),
            headers={"content-type": "application/json"},
        )

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert response.json()["code"] == "request.too_large"


def test_forwarded_headers_from_untrusted_peer_are_rejected_content_free() -> None:
    marker = "198.51.100.44"
    with _client() as client:
        response = client.get("/health/live", headers={"X-Forwarded-For": marker})

    assert response.status_code == 400
    assert response.json()["code"] == "proxy.untrusted"
    assert marker not in response.text


def test_forwarded_address_from_configured_trusted_peer_is_accepted() -> None:
    with _client(
        client_address=("192.0.2.10", 50_000),
        trusted_proxy_addresses="192.0.2.10",
    ) as client:
        response = client.get("/health/live", headers={"X-Forwarded-For": "198.51.100.44"})

    assert response.status_code == 200
    assert "198.51.100.44" not in response.text


def test_request_timeout_is_bounded_and_content_free() -> None:
    class _SlowRepository:
        async def resolve_index(self, index_version: UUID) -> None:
            del index_version
            await sleep(0.1)

    app = create_app(
        settings=_public_settings(request_timeout_seconds=0.01),
        engine=cast(AsyncEngine, _Engine()),
        search_repository=cast(SearchRepositoryPort, _SlowRepository()),
        search_embedding=cast(SearchEmbeddingPort, object()),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/search",
            json={"query": "private timeout marker", "index_version": str(UUID(int=1))},
        )

    assert response.status_code == 504
    assert response.json()["code"] == "request.timeout"
    assert "private timeout marker" not in response.text
