"""Content-free observability and provider-neutral generation controls."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from time import monotonic
from typing import Final
from uuid import UUID

from evalgate.application.ports import GenerationPort
from evalgate.domain.providers import GenerationInput, GenerationOutput, ProviderIdentity

_LOGGER = logging.getLogger(__name__)


class OperationalLimitCode(StrEnum):
    KILL_SWITCH = "generation.kill_switch"
    INPUT_TOKENS = "generation.input_tokens"
    OUTPUT_TOKENS = "generation.output_tokens"
    CLIENT_CONCURRENCY = "generation.client_concurrency"
    GLOBAL_CONCURRENCY = "generation.global_concurrency"
    DAILY_ALLOWANCE = "generation.daily_allowance"
    ACCOUNT_CAP = "generation.account_cap"
    COOLDOWN = "generation.cooldown"


class OperationalConfigurationErrorCode(StrEnum):
    PUBLIC_LIMITS_REQUIRED = "generation.public_limits_required"
    PARTIAL_LIMITS_FORBIDDEN = "generation.partial_limits_forbidden"


class OperationalConfigurationError(RuntimeError):
    """Typed, content-free configuration rejection for generation controls."""

    def __init__(self, code: OperationalConfigurationErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class OperationalLimitError(RuntimeError):
    """A stable operational rejection that never contains request content."""

    def __init__(self, code: OperationalLimitCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class GenerationLimits:
    """Declared deployment limits; values are supplied by deployment configuration."""

    maximum_input_tokens: int
    maximum_output_tokens: int
    per_client_concurrency: int
    global_concurrency: int
    daily_request_allowance: int
    provider_account_cap_usd: float
    cooldown_seconds: float

    def __post_init__(self) -> None:
        if (
            self.maximum_input_tokens < 1
            or self.maximum_output_tokens < 1
            or self.per_client_concurrency < 1
            or self.global_concurrency < 1
            or self.daily_request_allowance < 1
            or self.provider_account_cap_usd <= 0
            or self.cooldown_seconds < 0
        ):
            raise ValueError("generation operational limits are invalid")


def build_generation_limits(
    *,
    public_http: bool,
    maximum_input_tokens: int | None,
    maximum_output_tokens: int | None,
    per_client_concurrency: int | None,
    global_concurrency: int | None,
    daily_request_allowance: int | None,
    provider_account_cap_usd: float | None,
    cooldown_seconds: float,
) -> GenerationLimits | None:
    """Require a complete declared limit set before any public generation can exist."""

    values = (
        maximum_input_tokens,
        maximum_output_tokens,
        per_client_concurrency,
        global_concurrency,
        daily_request_allowance,
        provider_account_cap_usd,
    )
    if all(value is None for value in values):
        if public_http:
            raise OperationalConfigurationError(
                OperationalConfigurationErrorCode.PUBLIC_LIMITS_REQUIRED
            )
        return None
    if any(value is None for value in values):
        raise OperationalConfigurationError(
            OperationalConfigurationErrorCode.PARTIAL_LIMITS_FORBIDDEN
        )
    assert maximum_input_tokens is not None
    assert maximum_output_tokens is not None
    assert per_client_concurrency is not None
    assert global_concurrency is not None
    assert daily_request_allowance is not None
    assert provider_account_cap_usd is not None
    return GenerationLimits(
        maximum_input_tokens=maximum_input_tokens,
        maximum_output_tokens=maximum_output_tokens,
        per_client_concurrency=per_client_concurrency,
        global_concurrency=global_concurrency,
        daily_request_allowance=daily_request_allowance,
        provider_account_cap_usd=provider_account_cap_usd,
        cooldown_seconds=cooldown_seconds,
    )


@dataclass(frozen=True, slots=True)
class OperationalState:
    """Safe, operator-visible state without client identity or content."""

    generation_enabled: bool
    kill_switch_enabled: bool
    cooldown_active: bool
    active_global_generations: int
    daily_requests: int
    daily_cost_usd: float


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """The fixed, content-free event schema emitted through standard logging."""

    event: str
    operation: str
    status: str
    code: str | None
    request_id: UUID | None
    run_id: str | None
    duration_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None

    def __post_init__(self) -> None:
        if (
            not self.event
            or not self.operation
            or not self.status
            or self.duration_ms < 0
            or any(
                value is not None and value < 0
                for value in (self.input_tokens, self.output_tokens, self.cost_usd)
            )
        ):
            raise ValueError("telemetry event is invalid")


class StructuredTelemetry:
    """Emit only the fixed telemetry schema, never caller-provided content fields."""

    def emit(self, event: TelemetryEvent) -> None:
        _LOGGER.info(
            "evalgate operational event",
            extra={
                "event": event.event,
                "operation": event.operation,
                "status": event.status,
                "code": event.code,
                "request_id": str(event.request_id) if event.request_id is not None else None,
                "run_id": event.run_id,
                "duration_ms": event.duration_ms,
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "cost_usd": event.cost_usd,
            },
        )


_METRIC_LABELS: Final[dict[str, frozenset[str]]] = {
    "requests": frozenset({"operation", "status", "code"}),
    "generation_usage": frozenset({"status"}),
    "generation_rejections": frozenset({"code"}),
    "generation_state": frozenset({"state"}),
    "database_pool": frozenset({"state"}),
}


class OperationalMetrics:
    """Small in-memory counters with a reviewed, finite label vocabulary."""

    def __init__(self) -> None:
        self._values: Counter[tuple[str, tuple[tuple[str, str], ...]]] = Counter()

    def increment(self, name: str, /, **labels: str) -> None:
        allowed = _METRIC_LABELS.get(name)
        if allowed is None or frozenset(labels) != allowed:
            raise ValueError("metric labels are not in the reviewed cardinality schema")
        if any(not value or len(value) > 64 for value in labels.values()):
            raise ValueError("metric label values are invalid")
        self._values[(name, tuple(sorted(labels.items())))] += 1

    def snapshot(self) -> dict[tuple[str, tuple[tuple[str, str], ...]], int]:
        return dict(self._values)


class GenerationControl:
    """In-memory, process-local allowance, concurrency, cooldown, and kill-switch policy."""

    def __init__(
        self,
        limits: GenerationLimits,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        kill_switch_enabled: bool = False,
    ) -> None:
        self._limits = limits
        self._now = now
        self._kill_switch_enabled = kill_switch_enabled
        self._cooldown_until: datetime | None = None
        self._day: date | None = None
        self._daily_requests = 0
        self._daily_cost_usd = 0.0
        self._global_active = 0
        self._client_active: Counter[str] = Counter()
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        *,
        client_identity: str,
        input_tokens: int,
        configured_output_tokens: int,
        provider_account_spend_usd: float,
    ) -> None:
        if not client_identity or provider_account_spend_usd < 0:
            raise ValueError("generation control input is invalid")
        async with self._lock:
            now = self._now().astimezone(UTC)
            self._roll_day(now)
            if self._kill_switch_enabled:
                raise OperationalLimitError(OperationalLimitCode.KILL_SWITCH)
            if self._cooldown_until is not None and now < self._cooldown_until:
                raise OperationalLimitError(OperationalLimitCode.COOLDOWN)
            if input_tokens > self._limits.maximum_input_tokens:
                raise OperationalLimitError(OperationalLimitCode.INPUT_TOKENS)
            if configured_output_tokens > self._limits.maximum_output_tokens:
                raise OperationalLimitError(OperationalLimitCode.OUTPUT_TOKENS)
            if provider_account_spend_usd >= self._limits.provider_account_cap_usd:
                raise OperationalLimitError(OperationalLimitCode.ACCOUNT_CAP)
            if self._global_active >= self._limits.global_concurrency:
                raise OperationalLimitError(OperationalLimitCode.GLOBAL_CONCURRENCY)
            if self._client_active[client_identity] >= self._limits.per_client_concurrency:
                raise OperationalLimitError(OperationalLimitCode.CLIENT_CONCURRENCY)
            if self._daily_requests >= self._limits.daily_request_allowance:
                raise OperationalLimitError(OperationalLimitCode.DAILY_ALLOWANCE)
            self._daily_requests += 1
            self._global_active += 1
            self._client_active[client_identity] += 1

    async def release(
        self, *, client_identity: str, cost_usd: float = 0.0, outage: bool = False
    ) -> None:
        if cost_usd < 0:
            raise ValueError("generation cost is invalid")
        async with self._lock:
            now = self._now().astimezone(UTC)
            self._roll_day(now)
            if self._client_active[client_identity] < 1 or self._global_active < 1:
                raise RuntimeError("generation control release does not match an acquisition")
            self._client_active[client_identity] -= 1
            if self._client_active[client_identity] == 0:
                del self._client_active[client_identity]
            self._global_active -= 1
            self._daily_cost_usd += cost_usd
            if outage:
                self._cooldown_until = now + timedelta(seconds=self._limits.cooldown_seconds)

    async def set_kill_switch(self, enabled: bool) -> None:
        async with self._lock:
            self._kill_switch_enabled = enabled

    async def state(self) -> OperationalState:
        async with self._lock:
            now = self._now().astimezone(UTC)
            self._roll_day(now)
            return OperationalState(
                generation_enabled=not self._kill_switch_enabled
                and (self._cooldown_until is None or now >= self._cooldown_until),
                kill_switch_enabled=self._kill_switch_enabled,
                cooldown_active=self._cooldown_until is not None and now < self._cooldown_until,
                active_global_generations=self._global_active,
                daily_requests=self._daily_requests,
                daily_cost_usd=self._daily_cost_usd,
            )

    def _roll_day(self, now: datetime) -> None:
        if self._day != now.date():
            self._day = now.date()
            self._daily_requests = 0
            self._daily_cost_usd = 0.0


class ControlledGenerationPort:
    """Wrap exactly one configured provider; failures propagate without fallback."""

    def __init__(
        self,
        provider: GenerationPort,
        control: GenerationControl,
        telemetry: StructuredTelemetry,
        metrics: OperationalMetrics,
        *,
        client_identity: str,
        input_tokens: int,
        configured_output_tokens: int,
        provider_account_spend_usd: float,
        request_id: UUID | None = None,
        run_id: str | None = None,
    ) -> None:
        self._provider = provider
        self._control = control
        self._telemetry = telemetry
        self._metrics = metrics
        self._client_identity = client_identity
        self._input_tokens = input_tokens
        self._configured_output_tokens = configured_output_tokens
        self._provider_account_spend_usd = provider_account_spend_usd
        self._request_id = request_id
        self._run_id = run_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._provider.identity

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        started = monotonic()
        try:
            await self._control.acquire(
                client_identity=self._client_identity,
                input_tokens=self._input_tokens,
                configured_output_tokens=self._configured_output_tokens,
                provider_account_spend_usd=self._provider_account_spend_usd,
            )
        except OperationalLimitError as error:
            self._metrics.increment("generation_rejections", code=error.code.value)
            self._telemetry.emit(
                TelemetryEvent(
                    event="generation.rejected",
                    operation="generation",
                    status="rejected",
                    code=error.code.value,
                    request_id=self._request_id,
                    run_id=self._run_id,
                    duration_ms=round((monotonic() - started) * 1000, 3),
                )
            )
            raise
        try:
            output = await self._provider.generate(request)
        except asyncio.CancelledError:
            await self._control.release(client_identity=self._client_identity)
            self._metrics.increment(
                "requests", operation="generation", status="cancelled", code="stream.cancelled"
            )
            self._telemetry.emit(
                TelemetryEvent(
                    event="generation.cancelled",
                    operation="generation",
                    status="cancelled",
                    code="stream.cancelled",
                    request_id=self._request_id,
                    run_id=self._run_id,
                    duration_ms=round((monotonic() - started) * 1000, 3),
                )
            )
            raise
        except Exception:
            await self._control.release(client_identity=self._client_identity, outage=True)
            self._metrics.increment(
                "requests", operation="generation", status="failed", code="provider.unavailable"
            )
            self._telemetry.emit(
                TelemetryEvent(
                    event="generation.failed",
                    operation="generation",
                    status="failed",
                    code="provider.unavailable",
                    request_id=self._request_id,
                    run_id=self._run_id,
                    duration_ms=round((monotonic() - started) * 1000, 3),
                )
            )
            raise
        usage = output.usage
        await self._control.release(
            client_identity=self._client_identity,
            cost_usd=usage.cost_usd if usage is not None else 0.0,
        )
        self._metrics.increment("requests", operation="generation", status="completed", code="none")
        self._metrics.increment("generation_usage", status="completed")
        self._telemetry.emit(
            TelemetryEvent(
                event="generation.completed",
                operation="generation",
                status="completed",
                code=None,
                request_id=self._request_id,
                run_id=self._run_id,
                duration_ms=round((monotonic() - started) * 1000, 3),
                input_tokens=usage.input_tokens if usage is not None else None,
                output_tokens=usage.output_tokens if usage is not None else None,
                cost_usd=usage.cost_usd if usage is not None else None,
            )
        )
        return output
