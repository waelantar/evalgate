"""Framework-free runtime, route, outbound, and rate-identity security policy."""

from __future__ import annotations

import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from ipaddress import ip_address
from re import fullmatch
from typing import Literal
from urllib.parse import urlsplit

Environment = Literal["local", "ci", "trusted_evaluation", "public"]


class SecurityConfigurationErrorCode(StrEnum):
    """Stable, content-free reasons for rejecting runtime security configuration."""

    PUBLIC_ORIGIN_REQUIRED = "security.public_origin_required"
    ORIGIN_INVALID = "security.origin_invalid"
    RATE_SECRET_REQUIRED = "security.rate_secret_required"
    TRUSTED_PROXY_INVALID = "security.trusted_proxy_invalid"
    PROVIDER_ENDPOINT_FORBIDDEN = "security.provider_endpoint_forbidden"


class SecurityConfigurationError(RuntimeError):
    """Fail-closed runtime security configuration error."""

    def __init__(self, code: SecurityConfigurationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class EnvironmentPolicy:
    """Explicit capability matrix for each supported execution environment."""

    environment: Environment
    allow_ingestion: bool
    allow_result_import: bool
    allow_evaluation: bool
    public_http: bool


_ENVIRONMENT_POLICIES: dict[Environment, EnvironmentPolicy] = {
    "local": EnvironmentPolicy("local", True, True, True, False),
    "ci": EnvironmentPolicy("ci", True, False, True, False),
    "trusted_evaluation": EnvironmentPolicy("trusted_evaluation", False, False, True, False),
    "public": EnvironmentPolicy("public", False, False, False, True),
}


def environment_policy(environment: Environment) -> EnvironmentPolicy:
    """Resolve the reviewed capability matrix without implicit fallbacks."""

    return _ENVIRONMENT_POLICIES[environment]


@dataclass(frozen=True, slots=True)
class RuntimeSecurityConfiguration:
    """Validated server-side security inputs consumed by the HTTP adapter."""

    environment_policy: EnvironmentPolicy
    allowed_origins: tuple[str, ...]
    trusted_proxy_addresses: frozenset[str]
    request_body_limit_bytes: int
    request_timeout_seconds: float
    rate_identity_ttl_seconds: int
    rate_identity_secret: bytes | None = field(repr=False)


_PUBLIC_ROUTE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("GET", r"/health/(?:live|ready)"),
    ("POST", r"/api/v1/(?:search|ask)"),
    ("GET", r"/api/v1/evaluation-runs"),
    ("GET", r"/api/v1/evaluation-runs/[^/]+"),
    ("GET", r"/api/v1/evaluation-runs/[^/]+/cases"),
)


def public_route_allowed(method: str, path: str) -> bool:
    """Return whether a method/path is in the explicit public read-only matrix."""

    if method == "OPTIONS":
        return any(fullmatch(pattern, path) for _, pattern in _PUBLIC_ROUTE_PATTERNS)
    return any(
        method == allowed_method and fullmatch(pattern, path)
        for allowed_method, pattern in _PUBLIC_ROUTE_PATTERNS
    )


def _validate_origin(origin: str, *, require_https: bool) -> str:
    normalized = origin.strip()
    parsed = urlsplit(normalized)
    if (
        not normalized
        or "*" in normalized
        or parsed.scheme not in {"http", "https"}
        or (require_https and parsed.scheme != "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.ORIGIN_INVALID,
            "allowed origins must be exact HTTP origins without credentials, paths, or wildcards",
        )
    return normalized.rstrip("/")


def _validate_proxy(value: str) -> str:
    normalized = value.strip()
    try:
        ip_address(normalized)
    except ValueError as error:
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.TRUSTED_PROXY_INVALID,
            "trusted proxy entries must be literal IP addresses",
        ) from error
    return normalized


def build_runtime_security_configuration(
    *,
    environment: Environment,
    allowed_origins: str,
    trusted_proxy_addresses: str,
    request_body_limit_bytes: int,
    request_timeout_seconds: float,
    rate_identity_ttl_seconds: int,
    rate_identity_secret: str | None,
) -> RuntimeSecurityConfiguration:
    """Validate environment-specific inputs before an HTTP runtime is built."""

    policy = environment_policy(environment)
    origins = tuple(
        _validate_origin(value, require_https=policy.public_http)
        for value in allowed_origins.split(",")
        if value.strip()
    )
    if policy.public_http and not origins:
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.PUBLIC_ORIGIN_REQUIRED,
            "public mode requires at least one exact HTTPS browser origin",
        )
    if len(set(origins)) != len(origins):
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.ORIGIN_INVALID,
            "allowed origins must not contain duplicates",
        )
    proxies = frozenset(
        _validate_proxy(value) for value in trusted_proxy_addresses.split(",") if value.strip()
    )
    secret = rate_identity_secret.strip() if rate_identity_secret is not None else ""
    if policy.public_http and len(secret.encode("utf-8")) < 32:
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.RATE_SECRET_REQUIRED,
            "public mode requires a server-side rate identity secret of at least 32 bytes",
        )
    return RuntimeSecurityConfiguration(
        environment_policy=policy,
        allowed_origins=origins,
        trusted_proxy_addresses=proxies,
        request_body_limit_bytes=request_body_limit_bytes,
        request_timeout_seconds=request_timeout_seconds,
        rate_identity_ttl_seconds=rate_identity_ttl_seconds,
        rate_identity_secret=secret.encode("utf-8") if secret else None,
    )


_ALLOWED_PROVIDER_BASE_URLS = frozenset({"https://openrouter.ai/api/v1"})


def validate_provider_base_url(value: str) -> str:
    """Reject arbitrary/credential-bearing outbound provider endpoints."""

    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if (
        normalized not in _ALLOWED_PROVIDER_BASE_URLS
        or parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SecurityConfigurationError(
            SecurityConfigurationErrorCode.PROVIDER_ENDPOINT_FORBIDDEN,
            "provider base URL is not in the reviewed server-side allowlist",
        )
    return normalized


class ForwardedIdentityError(ValueError):
    """Forwarding metadata was supplied by an untrusted or malformed peer."""


def resolve_rate_address(
    *, peer_address: str, forwarded_for: str | None, trusted_proxy_addresses: frozenset[str]
) -> str:
    """Resolve a rate address only through an explicitly trusted edge."""

    if forwarded_for is None:
        return peer_address
    if peer_address not in trusted_proxy_addresses:
        raise ForwardedIdentityError("forwarded identity came from an untrusted peer")
    candidate = forwarded_for.split(",", maxsplit=1)[0].strip()
    try:
        return str(ip_address(candidate))
    except ValueError as error:
        raise ForwardedIdentityError("forwarded identity is invalid") from error


@dataclass(frozen=True, slots=True)
class RateIdentity:
    """Short-lived non-reversible identity safe for in-memory rate accounting."""

    pseudonym: str
    expires_at: datetime


def pseudonymize_rate_address(
    *, address: str, secret: bytes, ttl_seconds: int, now: datetime
) -> RateIdentity:
    """Key and rotate an address without retaining or logging the raw value."""

    normalized_now = now.astimezone(UTC)
    bucket = int(normalized_now.timestamp()) // ttl_seconds
    message = f"{bucket}:{address}".encode()
    digest = hmac.new(secret, message, sha256).hexdigest()[:32]
    expires_at = datetime.fromtimestamp((bucket + 1) * ttl_seconds, tz=UTC)
    return RateIdentity(pseudonym=f"rate-v1:{digest}", expires_at=expires_at)
