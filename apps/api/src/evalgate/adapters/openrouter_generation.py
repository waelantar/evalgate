"""Governed OpenRouter generation adapter for the protected live evaluation suite."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import SecretStr

from evalgate.application.runtime_security import (
    SecurityConfigurationError,
    validate_provider_base_url,
)
from evalgate.domain.providers import (
    GenerationInput,
    GenerationOutput,
    GenerationUsage,
    ProviderIdentity,
    ProviderMode,
)

OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_MODEL_REVISION = "deepseek-v4-flash-2026-04-24"
OPENROUTER_INPUT_PRICE_PER_MILLION = 0.14
OPENROUTER_OUTPUT_PRICE_PER_MILLION = 0.28

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "answer", "citations"],
    "properties": {
        "status": {"enum": ["answered", "insufficient_support"]},
        "answer": {"type": "string", "minLength": 1, "maxLength": 4000},
        "citations": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["answer_start", "answer_end", "evidence_ids"],
                "properties": {
                    "answer_start": {"type": "integer", "minimum": 0},
                    "answer_end": {"type": "integer", "minimum": 1},
                    "evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


class OpenRouterGenerationErrorCode(StrEnum):
    """Stable, content-free OpenRouter adapter failure categories."""

    SECRET_MISSING = "openrouter.secret_missing"
    REQUEST_FAILED = "openrouter.request_failed"
    RESPONSE_INVALID = "openrouter.response_invalid"
    CAP_EXCEEDED = "openrouter.cap_exceeded"


class OpenRouterGenerationError(RuntimeError):
    """OpenRouter adapter error that never includes prompt, answer, or key material."""

    def __init__(
        self, code: OpenRouterGenerationErrorCode, message: str, *, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class _HTTPResponse(Protocol):
    status: int

    def read(self) -> bytes: ...


UrlOpen = Callable[[Request, float], _HTTPResponse]


def _default_urlopen(request: Request, timeout: float) -> _HTTPResponse:
    return cast(_HTTPResponse, urlopen(request, timeout=timeout))


@dataclass(frozen=True, slots=True)
class OpenRouterGenerationConfig:
    """Approved OpenRouter posture for EG-015."""

    api_key: SecretStr
    model: str = OPENROUTER_MODEL
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_seconds: float = 30.0
    budget_usd: float = 4.60
    stop_usd: float = 4.14
    max_output_tokens: int = 1200
    response_schema_name: str = "evalgate_grounded_answer"
    response_schema: dict[str, Any] | None = None
    transient_retries: int = 2
    cooldown_seconds: float = 2.0
    input_price_per_million: float = OPENROUTER_INPUT_PRICE_PER_MILLION
    output_price_per_million: float = OPENROUTER_OUTPUT_PRICE_PER_MILLION

    def __post_init__(self) -> None:
        if not self.api_key.get_secret_value().strip():
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.SECRET_MISSING,
                "OpenRouter API key is not configured",
            )
        if self.model != OPENROUTER_MODEL:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter model is not the approved EG-015 model",
            )
        try:
            normalized_base_url = validate_provider_base_url(self.base_url)
        except SecurityConfigurationError as error:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter endpoint is not in the reviewed allowlist",
            ) from error
        object.__setattr__(self, "base_url", normalized_base_url)
        if (
            self.timeout_seconds <= 0
            or self.max_output_tokens < 1
            or self.transient_retries < 0
            or self.cooldown_seconds < 0
        ):
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter request bounds are invalid",
            )
        if self.budget_usd <= 0 or self.stop_usd <= 0 or self.stop_usd > self.budget_usd:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.CAP_EXCEEDED,
                "OpenRouter live-evaluation budget is invalid",
            )


class OpenRouterGenerationAdapter:
    """Call one approved OpenRouter model with no fallback or browser-visible secret."""

    identity = ProviderIdentity(
        mode=ProviderMode.LIVE,
        name="openrouter/deepseek/deepseek-v4-flash",
        revision=OPENROUTER_MODEL_REVISION,
    )

    def __init__(
        self, config: OpenRouterGenerationConfig, *, opener: UrlOpen = _default_urlopen
    ) -> None:
        self._config = config
        self._opener = opener
        self._spent_usd = 0.0

    @property
    def spent_usd(self) -> float:
        return self._spent_usd

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        """Generate one bounded structured response and record estimated cost."""

        if self._spent_usd >= self._config.stop_usd:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.CAP_EXCEEDED,
                "OpenRouter live-evaluation stop limit has been reached",
            )
        for attempt in range(self._config.transient_retries + 1):
            try:
                return await asyncio.to_thread(self._generate_sync, request)
            except OpenRouterGenerationError as error:
                if not error.retryable or attempt >= self._config.transient_retries:
                    raise
                await asyncio.sleep(self._config.cooldown_seconds)
        raise AssertionError("bounded OpenRouter retry loop exhausted")

    def _generate_sync(self, request: GenerationInput) -> GenerationOutput:
        payload = {
            "model": self._config.model,
            "input": request.text,
            "stream": False,
            "temperature": 0,
            "max_output_tokens": self._config.max_output_tokens,
            "reasoning": {"effort": "high", "exclude": True},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": self._config.response_schema_name,
                    "strict": True,
                    "schema": self._config.response_schema or _OUTPUT_SCHEMA,
                },
            },
            "provider": {
                "zdr": True,
                "data_collection": "deny",
                "allow_fallbacks": False,
                "require_parameters": True,
                "sort": "price",
                "max_price": {"prompt": 0.14, "completion": 0.28},
            },
        }
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        http_request = Request(
            f"{self._config.base_url.rstrip('/')}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self._config.api_key.get_secret_value()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-OpenRouter-Title": "EvalGate EG-015 governed live evaluation",
            },
            method="POST",
        )
        try:
            response = self._opener(http_request, self._config.timeout_seconds)
            raw = response.read()
        except HTTPError as error:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter request failed",
                retryable=error.code in {429, 503},
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter request failed",
                retryable=True,
            ) from error
        if response.status < 200 or response.status >= 300:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.REQUEST_FAILED,
                "OpenRouter request failed",
            )

        try:
            value = json.loads(raw)
            content = _parse_response_text(value)
            if not isinstance(content, str) or not content.strip():
                raise ValueError("missing content")
            usage = _parse_usage(
                value.get("usage", {}),
                input_price_per_million=self._config.input_price_per_million,
                output_price_per_million=self._config.output_price_per_million,
            )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.RESPONSE_INVALID,
                "OpenRouter response was invalid",
            ) from error

        if self._spent_usd + usage.cost_usd > self._config.stop_usd:
            raise OpenRouterGenerationError(
                OpenRouterGenerationErrorCode.CAP_EXCEEDED,
                "OpenRouter live-evaluation stop limit would be exceeded",
            )
        self._spent_usd += usage.cost_usd
        return GenerationOutput(text=content, identity=self.identity, usage=usage)


def _parse_usage(
    value: Any, *, input_price_per_million: float, output_price_per_million: float
) -> GenerationUsage:
    if not isinstance(value, dict):
        raise ValueError("usage is missing")
    input_tokens = _non_negative_int(value.get("prompt_tokens", value.get("input_tokens", 0)))
    output_tokens = _non_negative_int(value.get("completion_tokens", value.get("output_tokens", 0)))
    total_tokens = _non_negative_int(value.get("total_tokens", input_tokens + output_tokens))
    explicit_cost = value.get("cost")
    if (
        isinstance(explicit_cost, (int, float))
        and not isinstance(explicit_cost, bool)
        and explicit_cost >= 0
    ):
        cost_usd = float(explicit_cost)
    else:
        cost_usd = (
            input_tokens * input_price_per_million + output_tokens * output_price_per_million
        ) / 1_000_000
    return GenerationUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
    )


def _parse_response_text(value: Any) -> str:
    if not isinstance(value, dict):
        raise ValueError("response must be an object")
    output_text = value.get("output_text")
    if isinstance(output_text, str):
        return output_text
    output = value.get("output")
    if not isinstance(output, list):
        raise ValueError("response output is missing")
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                parts.append(part["text"])
    if not parts:
        raise ValueError("response output text is missing")
    return "".join(parts)


def _non_negative_int(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("usage token counts must be non-negative integers")
    return value
