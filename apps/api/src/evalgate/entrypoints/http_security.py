"""HTTP-only enforcement for the reviewed EvalGate runtime security policy."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Final

from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from evalgate.application.runtime_security import (
    ForwardedIdentityError,
    RuntimeSecurityConfiguration,
    pseudonymize_rate_address,
    public_route_allowed,
    resolve_rate_address,
)

_FORWARDED_HEADERS: Final = frozenset(
    {"forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-real-ip"}
)
_SECURITY_HEADERS: Final[dict[str, str]] = {
    "Content-Security-Policy": (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; "
        "script-src 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _safe_problem(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": f"urn:evalgate:problem:{code}",
            "title": "Request rejected" if status < 500 else "Request timed out",
            "status": status,
            "detail": detail,
            "code": code,
        },
        media_type="application/problem+json",
    )


class RuntimeSecurityMiddleware:
    """Enforce public routes, body/time bounds, trusted edges, and safe headers."""

    def __init__(self, app: ASGIApp, *, configuration: RuntimeSecurityConfiguration) -> None:
        self.app = app
        self._configuration = configuration

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        policy = self._configuration.environment_policy
        method = scope["method"]
        path = scope["path"]
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope["headers"]
        }
        if policy.public_http and not public_route_allowed(method, path):
            response = _safe_problem(
                404, "route.unavailable", "The requested route is unavailable."
            )
            self._with_security_headers(response, public=True)
            await response(scope, receive, send)
            return

        if method in {"POST", "PUT", "PATCH"}:
            content_length = headers.get("content-length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError:
                    declared_length = self._configuration.request_body_limit_bytes + 1
                if declared_length > self._configuration.request_body_limit_bytes:
                    response = _safe_problem(
                        413, "request.too_large", "The request body exceeds the configured limit."
                    )
                    self._with_security_headers(response, public=policy.public_http)
                    await response(scope, receive, send)
                    return

        if policy.public_http:
            forwarded_present = any(name in headers for name in _FORWARDED_HEADERS)
            forwarded_for = headers.get("x-forwarded-for")
            client = scope.get("client")
            peer_address = client[0] if client is not None else "unknown-peer"
            if forwarded_present and forwarded_for is None:
                response = _safe_problem(
                    400, "proxy.untrusted", "Forwarding metadata is not accepted from this peer."
                )
                self._with_security_headers(response, public=True)
                await response(scope, receive, send)
                return
            try:
                rate_address = resolve_rate_address(
                    peer_address=peer_address,
                    forwarded_for=forwarded_for,
                    trusted_proxy_addresses=self._configuration.trusted_proxy_addresses,
                )
            except ForwardedIdentityError:
                response = _safe_problem(
                    400, "proxy.untrusted", "Forwarding metadata is not accepted from this peer."
                )
                self._with_security_headers(response, public=True)
                await response(scope, receive, send)
                return
            secret = self._configuration.rate_identity_secret
            if secret is None:  # Configuration validation makes this unreachable in public mode.
                response = _safe_problem(
                    503, "security.configuration", "The public security policy is unavailable."
                )
                self._with_security_headers(response, public=True)
                await response(scope, receive, send)
                return
            scope.setdefault("state", {})["rate_identity"] = pseudonymize_rate_address(
                address=rate_address,
                secret=secret,
                ttl_seconds=self._configuration.rate_identity_ttl_seconds,
                now=datetime.now(UTC),
            )

        received_bytes = 0
        response_started = False
        body_too_large = False

        async def bounded_receive() -> Message:
            nonlocal body_too_large, received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._configuration.request_body_limit_bytes:
                    body_too_large = True
                    return {"type": "http.disconnect"}
            return message

        async def security_send(message: Message) -> None:
            nonlocal response_started
            if body_too_large:
                return
            if message["type"] == "http.response.start":
                response_started = True
                response_headers = {
                    key.decode("latin-1").lower(): (key, value)
                    for key, value in message.get("headers", [])
                }
                additions = dict(_SECURITY_HEADERS)
                if policy.public_http:
                    additions["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                if "cache-control" not in response_headers:
                    additions["Cache-Control"] = "no-store"
                raw_headers = list(message.get("headers", []))
                for name, value in additions.items():
                    lower_name = name.lower()
                    if lower_name in response_headers:
                        raw_headers = [
                            pair
                            for pair in raw_headers
                            if pair[0].decode("latin-1").lower() != lower_name
                        ]
                    raw_headers.append((name.encode("latin-1"), value.encode("latin-1")))
                message["headers"] = raw_headers
            await send(message)

        try:
            async with asyncio.timeout(self._configuration.request_timeout_seconds):
                try:
                    await self.app(scope, bounded_receive, security_send)
                except Exception:
                    if not body_too_large:
                        raise
            if body_too_large:
                response = _safe_problem(
                    413, "request.too_large", "The request body exceeds the configured limit."
                )
                self._with_security_headers(response, public=policy.public_http)
                await response(scope, receive, send)
        except TimeoutError:
            if response_started:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            else:
                response = _safe_problem(
                    504, "request.timeout", "The request exceeded the configured time limit."
                )
                self._with_security_headers(response, public=policy.public_http)
                await response(scope, receive, send)

    @staticmethod
    def _with_security_headers(response: Response, *, public: bool) -> None:
        for name, value in _SECURITY_HEADERS.items():
            response.headers[name] = value
        if public:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
