"""EG-013C content-free telemetry and generation-control tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from evalgate.application.operations import (
    ControlledGenerationPort,
    GenerationControl,
    GenerationLimits,
    OperationalConfigurationError,
    OperationalConfigurationErrorCode,
    OperationalLimitCode,
    OperationalLimitError,
    OperationalMetrics,
    StructuredTelemetry,
    build_generation_limits,
)
from evalgate.domain.providers import (
    GenerationInput,
    GenerationOutput,
    GenerationUsage,
    ProviderIdentity,
    ProviderMode,
)

_IDENTITY = ProviderIdentity(ProviderMode.LIVE, "approved-provider", "reviewed-revision")
_REQUEST_ID = UUID(int=1)


def _limits(**overrides: object) -> GenerationLimits:
    values: dict[str, object] = {
        "maximum_input_tokens": 10,
        "maximum_output_tokens": 8,
        "per_client_concurrency": 1,
        "global_concurrency": 2,
        "daily_request_allowance": 2,
        "provider_account_cap_usd": 1.0,
        "cooldown_seconds": 60,
    }
    values.update(overrides)
    return GenerationLimits(**values)  # type: ignore[arg-type]


class _Provider:
    identity = _IDENTITY

    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = 0

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return GenerationOutput(
            text="{}",
            identity=self.identity,
            usage=GenerationUsage(3, 2, 5, 0.01),
        )


def _port(
    provider: _Provider,
    control: GenerationControl,
    telemetry: StructuredTelemetry,
    metrics: OperationalMetrics,
    **overrides: object,
) -> ControlledGenerationPort:
    values: dict[str, object] = {
        "client_identity": "rate-v1:pseudonym",
        "input_tokens": 3,
        "configured_output_tokens": 5,
        "provider_account_spend_usd": 0.0,
        "request_id": _REQUEST_ID,
        "run_id": "run-1",
    }
    values.update(overrides)
    return ControlledGenerationPort(provider, control, telemetry, metrics, **values)  # type: ignore[arg-type]


def test_success_telemetry_is_structured_and_redacts_prompt_and_identity(
    caplog: pytest.LogCaptureFixture,
) -> None:
    control = GenerationControl(_limits())
    metrics = OperationalMetrics()
    marker = "private question marker"
    with caplog.at_level("INFO"):
        output = asyncio.run(
            _port(_Provider(), control, StructuredTelemetry(), metrics).generate(
                GenerationInput(marker)
            )
        )

    assert output.identity == _IDENTITY
    record = next(
        record
        for record in caplog.records
        if record.__dict__.get("event") == "generation.completed"
    )
    assert record.__dict__["request_id"] == str(_REQUEST_ID)
    assert record.__dict__["run_id"] == "run-1"
    assert record.__dict__["input_tokens"] == 3
    assert record.__dict__["output_tokens"] == 2
    assert marker not in caplog.text
    assert "rate-v1:pseudonym" not in caplog.text
    assert (
        metrics.snapshot()[
            ("requests", (("code", "none"), ("operation", "generation"), ("status", "completed")))
        ]
        == 1
    )


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"input_tokens": 11}, OperationalLimitCode.INPUT_TOKENS),
        ({"configured_output_tokens": 9}, OperationalLimitCode.OUTPUT_TOKENS),
        ({"provider_account_spend_usd": 1.0}, OperationalLimitCode.ACCOUNT_CAP),
    ],
)
def test_token_and_account_caps_reject_before_call(
    override: dict[str, object], code: OperationalLimitCode
) -> None:
    provider = _Provider()
    with pytest.raises(OperationalLimitError) as captured:
        asyncio.run(
            _port(
                provider,
                GenerationControl(_limits()),
                StructuredTelemetry(),
                OperationalMetrics(),
                **override,
            ).generate(GenerationInput("prompt"))
        )
    assert captured.value.code is code
    assert provider.calls == 0


def test_concurrency_daily_allowance_cooldown_and_kill_switch_reject_safely() -> None:
    now = datetime(2026, 9, 13, tzinfo=UTC)
    control = GenerationControl(_limits(daily_request_allowance=2), now=lambda: now)

    async def exercise() -> None:
        await control.acquire(
            client_identity="client-a",
            input_tokens=1,
            configured_output_tokens=1,
            provider_account_spend_usd=0,
        )
        with pytest.raises(OperationalLimitError) as client_limit:
            await control.acquire(
                client_identity="client-a",
                input_tokens=1,
                configured_output_tokens=1,
                provider_account_spend_usd=0,
            )
        assert client_limit.value.code is OperationalLimitCode.CLIENT_CONCURRENCY
        await control.release(client_identity="client-a", outage=True)
        with pytest.raises(OperationalLimitError) as cooldown:
            await control.acquire(
                client_identity="client-b",
                input_tokens=1,
                configured_output_tokens=1,
                provider_account_spend_usd=0,
            )
        assert cooldown.value.code is OperationalLimitCode.COOLDOWN
        await control.set_kill_switch(True)
        with pytest.raises(OperationalLimitError) as kill_switch:
            await control.acquire(
                client_identity="client-b",
                input_tokens=1,
                configured_output_tokens=1,
                provider_account_spend_usd=0,
            )
        assert kill_switch.value.code is OperationalLimitCode.KILL_SWITCH
        state = await control.state()
        assert state.kill_switch_enabled
        assert not state.generation_enabled

    asyncio.run(exercise())

    global_control = GenerationControl(_limits(global_concurrency=1))

    async def global_exercise() -> None:
        await global_control.acquire(
            client_identity="client-global-a",
            input_tokens=1,
            configured_output_tokens=1,
            provider_account_spend_usd=0,
        )
        with pytest.raises(OperationalLimitError) as global_limit:
            await global_control.acquire(
                client_identity="client-global-b",
                input_tokens=1,
                configured_output_tokens=1,
                provider_account_spend_usd=0,
            )
        assert global_limit.value.code is OperationalLimitCode.GLOBAL_CONCURRENCY

    asyncio.run(global_exercise())

    daily_now = [now]
    daily = GenerationControl(_limits(daily_request_allowance=1), now=lambda: daily_now[0])

    async def daily_exercise() -> None:
        await daily.acquire(
            client_identity="client-c",
            input_tokens=1,
            configured_output_tokens=1,
            provider_account_spend_usd=0,
        )
        await daily.release(client_identity="client-c")
        with pytest.raises(OperationalLimitError) as allowance:
            await daily.acquire(
                client_identity="client-d",
                input_tokens=1,
                configured_output_tokens=1,
                provider_account_spend_usd=0,
            )
        assert allowance.value.code is OperationalLimitCode.DAILY_ALLOWANCE
        daily_now[0] = now + timedelta(days=1)
        await daily.acquire(
            client_identity="client-d",
            input_tokens=1,
            configured_output_tokens=1,
            provider_account_spend_usd=0,
        )

    asyncio.run(daily_exercise())


def test_provider_outage_sets_cooldown_and_never_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _Provider(failure=RuntimeError("provider private failure"))
    control = GenerationControl(_limits())
    with caplog.at_level("INFO"), pytest.raises(RuntimeError):
        asyncio.run(
            _port(provider, control, StructuredTelemetry(), OperationalMetrics()).generate(
                GenerationInput("private prompt")
            )
        )
    assert provider.calls == 1
    assert "private prompt" not in caplog.text
    assert "provider private failure" not in caplog.text
    with pytest.raises(OperationalLimitError) as cooldown:
        asyncio.run(
            _port(provider, control, StructuredTelemetry(), OperationalMetrics()).generate(
                GenerationInput("next")
            )
        )
    assert cooldown.value.code is OperationalLimitCode.COOLDOWN
    assert provider.calls == 1


def test_cancellation_releases_the_permit_and_emits_content_free_telemetry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cancelled = asyncio.Event()

    class _CancellingProvider(_Provider):
        async def generate(self, request: GenerationInput) -> GenerationOutput:
            del request
            cancelled.set()
            raise asyncio.CancelledError

    control = GenerationControl(_limits())
    with caplog.at_level("INFO"), pytest.raises(asyncio.CancelledError):
        asyncio.run(
            _port(
                _CancellingProvider(), control, StructuredTelemetry(), OperationalMetrics()
            ).generate(GenerationInput("private cancellation prompt"))
        )
    assert cancelled.is_set()
    record = next(
        record
        for record in caplog.records
        if record.__dict__.get("event") == "generation.cancelled"
    )
    assert record.__dict__["code"] == "stream.cancelled"
    assert "private cancellation prompt" not in caplog.text
    state = asyncio.run(control.state())
    assert state.active_global_generations == 0


def test_metric_schema_rejects_high_cardinality_or_unknown_labels() -> None:
    metrics = OperationalMetrics()
    metrics.increment("requests", operation="search", status="completed", code="none")
    with pytest.raises(ValueError):
        metrics.increment(
            "requests", operation="search", status="completed", code="none", request_id="1"
        )
    with pytest.raises(ValueError):
        metrics.increment("unknown", status="completed")


def test_public_generation_requires_one_complete_declared_limit_set() -> None:
    with pytest.raises(OperationalConfigurationError) as missing:
        build_generation_limits(
            public_http=True,
            maximum_input_tokens=None,
            maximum_output_tokens=None,
            per_client_concurrency=None,
            global_concurrency=None,
            daily_request_allowance=None,
            provider_account_cap_usd=None,
            cooldown_seconds=0,
        )
    assert missing.value.code is OperationalConfigurationErrorCode.PUBLIC_LIMITS_REQUIRED
    with pytest.raises(OperationalConfigurationError) as partial:
        build_generation_limits(
            public_http=False,
            maximum_input_tokens=1,
            maximum_output_tokens=None,
            per_client_concurrency=None,
            global_concurrency=None,
            daily_request_allowance=None,
            provider_account_cap_usd=None,
            cooldown_seconds=0,
        )
    assert partial.value.code is OperationalConfigurationErrorCode.PARTIAL_LIMITS_FORBIDDEN
