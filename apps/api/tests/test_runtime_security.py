"""EG-013A runtime policy, outbound allowlist, and minimized identity tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from evalgate.application.runtime_security import (
    ForwardedIdentityError,
    SecurityConfigurationError,
    SecurityConfigurationErrorCode,
    build_runtime_security_configuration,
    environment_policy,
    pseudonymize_rate_address,
    public_route_allowed,
    resolve_rate_address,
    validate_provider_base_url,
)
from evalgate.config import Settings


def test_environment_capability_matrix_is_explicit_and_public_is_non_mutating() -> None:
    assert environment_policy("local") == environment_policy("local")
    assert environment_policy("local").allow_result_import
    assert environment_policy("ci").allow_ingestion
    assert not environment_policy("ci").allow_result_import
    assert environment_policy("trusted_evaluation").allow_evaluation
    assert not environment_policy("trusted_evaluation").allow_ingestion
    public = environment_policy("public")
    assert public.public_http
    assert not public.allow_ingestion
    assert not public.allow_result_import
    assert not public.allow_evaluation


@pytest.mark.parametrize(
    ("method", "path", "allowed"),
    [
        ("GET", "/health/live", True),
        ("GET", "/health/ready", True),
        ("POST", "/api/v1/search", True),
        ("POST", "/api/v1/ask", True),
        ("GET", "/api/v1/evaluation-runs", True),
        ("GET", "/api/v1/evaluation-runs/run-1", True),
        ("GET", "/api/v1/evaluation-runs/run-1/cases", True),
        ("POST", "/api/v1/evaluation-runs", False),
        ("POST", "/api/v1/evaluation-runs/run-1/import", False),
        ("GET", "/openapi.json", False),
        ("GET", "/docs", False),
    ],
)
def test_public_route_matrix(method: str, path: str, allowed: bool) -> None:
    assert public_route_allowed(method, path) is allowed


def test_public_configuration_requires_exact_https_origin_and_rate_secret() -> None:
    with pytest.raises(SecurityConfigurationError) as missing_secret:
        Settings(
            environment="public",
            allowed_origins="https://demo.example",
        ).runtime_security_configuration()
    assert missing_secret.value.code is SecurityConfigurationErrorCode.RATE_SECRET_REQUIRED

    for origin in ("*", "http://demo.example", "https://demo.example/path", "javascript:x"):
        with pytest.raises(SecurityConfigurationError) as invalid_origin:
            Settings(
                environment="public",
                allowed_origins=origin,
                rate_identity_secret=SecretStr("s" * 32),
            ).runtime_security_configuration()
        assert invalid_origin.value.code is SecurityConfigurationErrorCode.ORIGIN_INVALID


def test_public_configuration_accepts_only_literal_trusted_proxy_addresses() -> None:
    configuration = Settings(
        environment="public",
        allowed_origins="https://demo.example",
        rate_identity_secret=SecretStr("s" * 32),
        trusted_proxy_addresses="192.0.2.10,2001:db8::10",
    ).runtime_security_configuration()
    assert configuration.trusted_proxy_addresses == frozenset({"192.0.2.10", "2001:db8::10"})

    with pytest.raises(SecurityConfigurationError) as invalid_proxy:
        Settings(
            environment="public",
            allowed_origins="https://demo.example",
            rate_identity_secret=SecretStr("s" * 32),
            trusted_proxy_addresses="edge.example",
        ).runtime_security_configuration()
    assert invalid_proxy.value.code is SecurityConfigurationErrorCode.TRUSTED_PROXY_INVALID


def test_provider_endpoint_allowlist_rejects_ssrf_and_credentials() -> None:
    assert validate_provider_base_url("https://openrouter.ai/api/v1/") == (
        "https://openrouter.ai/api/v1"
    )
    for value in (
        "http://openrouter.ai/api/v1",
        "https://openrouter.ai.evil.example/api/v1",
        "https://" + "user" + ":" + "pass" + "@openrouter.ai/api/v1",
        "https://openrouter.ai/api/v1?redirect=http://127.0.0.1",
        "http://127.0.0.1:8000",
    ):
        with pytest.raises(SecurityConfigurationError) as captured:
            validate_provider_base_url(value)
        assert captured.value.code is SecurityConfigurationErrorCode.PROVIDER_ENDPOINT_FORBIDDEN


def test_forwarded_identity_requires_a_trusted_edge() -> None:
    with pytest.raises(ForwardedIdentityError):
        resolve_rate_address(
            peer_address="192.0.2.20",
            forwarded_for="198.51.100.4",
            trusted_proxy_addresses=frozenset({"192.0.2.10"}),
        )
    assert (
        resolve_rate_address(
            peer_address="192.0.2.10",
            forwarded_for="198.51.100.4, 192.0.2.11",
            trusted_proxy_addresses=frozenset({"192.0.2.10"}),
        )
        == "198.51.100.4"
    )
    with pytest.raises(ForwardedIdentityError):
        resolve_rate_address(
            peer_address="192.0.2.10",
            forwarded_for="not-an-ip",
            trusted_proxy_addresses=frozenset({"192.0.2.10"}),
        )


def test_rate_identity_is_keyed_non_reversible_and_rotates_at_ttl() -> None:
    secret = b"s" * 32
    now = datetime(2026, 9, 13, 10, 0, 1, tzinfo=UTC)
    first = pseudonymize_rate_address(
        address="198.51.100.4", secret=secret, ttl_seconds=300, now=now
    )
    same_bucket = pseudonymize_rate_address(
        address="198.51.100.4", secret=secret, ttl_seconds=300, now=now + timedelta(seconds=10)
    )
    next_bucket = pseudonymize_rate_address(
        address="198.51.100.4", secret=secret, ttl_seconds=300, now=first.expires_at
    )
    other_secret = pseudonymize_rate_address(
        address="198.51.100.4", secret=b"t" * 32, ttl_seconds=300, now=now
    )

    assert first.pseudonym == same_bucket.pseudonym
    assert first.pseudonym != next_bucket.pseudonym
    assert first.pseudonym != other_secret.pseudonym
    assert "198.51.100.4" not in first.pseudonym
    assert len(first.pseudonym) == len("rate-v1:") + 32


def test_builder_does_not_retain_public_secret_as_text() -> None:
    configuration = build_runtime_security_configuration(
        environment="public",
        allowed_origins="https://demo.example",
        trusted_proxy_addresses="",
        request_body_limit_bytes=16_384,
        request_timeout_seconds=30,
        rate_identity_ttl_seconds=300,
        rate_identity_secret="s" * 32,
    )
    assert configuration.rate_identity_secret == b"s" * 32
    assert "s" * 32 not in repr(configuration)
