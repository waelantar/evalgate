"""OpenRouter live adapter contract, cap, and redaction tests."""

from __future__ import annotations

import asyncio
import json
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from pydantic import SecretStr

from evalgate.adapters.openrouter_generation import (
    OpenRouterGenerationAdapter,
    OpenRouterGenerationConfig,
    OpenRouterGenerationError,
    OpenRouterGenerationErrorCode,
)
from evalgate.domain.providers import GenerationInput, ProviderMode


class _Response:
    status = 200

    def __init__(self, value: dict[str, object]) -> None:
        self._value = value

    def read(self) -> bytes:
        return json.dumps(self._value).encode("utf-8")


def _completion(*, content: str = "{}.", cost: float = 0.001) -> dict[str, object]:
    return {
        "output_text": content,
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": cost},
    }


def test_openrouter_request_enforces_approved_policy_without_leaking_key() -> None:
    captured: dict[str, object] = {}

    def opener(request: Request, timeout: float) -> _Response:
        captured["timeout"] = timeout
        captured["url"] = request.full_url
        raw_body = request.data
        assert isinstance(raw_body, bytes | bytearray)
        captured["body"] = json.loads(raw_body)
        captured["authorization"] = request.get_header("Authorization")
        return _Response(
            _completion(
                content='{"status":"insufficient_support","answer":"No support.","citations":[]}'
            )
        )

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(api_key=SecretStr("secret-key")), opener=opener
    )
    output = asyncio.run(adapter.generate(GenerationInput("prompt-body")))

    assert output.identity.mode is ProviderMode.LIVE
    assert output.usage is not None
    assert output.usage.cost_usd == 0.001
    assert captured["url"] == "https://openrouter.ai/api/v1/responses"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "deepseek/deepseek-v4-flash"
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert body["max_output_tokens"] == 1200
    assert body["reasoning"] == {"effort": "high", "exclude": True}
    assert "messages" not in body
    assert "response_format" not in body
    text = body["text"]
    assert isinstance(text, dict)
    text_format = text["format"]
    assert isinstance(text_format, dict)
    assert text_format["type"] == "json_schema"
    assert text_format["name"] == "evalgate_grounded_answer"
    assert text_format["strict"] is True
    assert isinstance(text_format["schema"], dict)
    assert body["provider"] == {
        "zdr": True,
        "data_collection": "deny",
        "allow_fallbacks": False,
        "require_parameters": True,
        "sort": "price",
        "max_price": {"prompt": 0.05, "completion": 0.14},
    }
    assert "secret-key" not in json.dumps(body)
    assert captured["authorization"] == "Bearer secret-key"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://openrouter.ai/api/v1",
        "https://openrouter.ai.evil.example/api/v1",
        "http://127.0.0.1:8000",
    ],
)
def test_openrouter_adapter_rejects_non_allowlisted_endpoint(base_url: str) -> None:
    with pytest.raises(OpenRouterGenerationError) as captured:
        OpenRouterGenerationConfig(api_key=SecretStr("secret"), base_url=base_url)

    assert captured.value.code is OpenRouterGenerationErrorCode.REQUEST_FAILED
    assert base_url not in str(captured.value)


def test_openrouter_errors_are_typed_and_content_free() -> None:
    def opener(_: Request, __: float) -> _Response:
        return _Response({"choices": []})

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(api_key=SecretStr("secret-key")), opener=opener
    )
    with pytest.raises(OpenRouterGenerationError) as captured:
        asyncio.run(adapter.generate(GenerationInput("private prompt marker")))

    assert captured.value.code is OpenRouterGenerationErrorCode.RESPONSE_INVALID
    assert "private prompt marker" not in str(captured.value)
    assert "secret-key" not in str(captured.value)


def test_openrouter_stop_limit_blocks_overspend() -> None:
    def opener(_: Request, __: float) -> _Response:
        return _Response(_completion(cost=0.50))

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(api_key=SecretStr("secret-key"), stop_usd=0.01),
        opener=opener,
    )
    with pytest.raises(OpenRouterGenerationError) as captured:
        asyncio.run(adapter.generate(GenerationInput("prompt")))

    assert captured.value.code is OpenRouterGenerationErrorCode.CAP_EXCEEDED


def test_openrouter_retries_transient_rate_limit_without_fallback() -> None:
    calls = 0

    def opener(_: Request, __: float) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPError("https://openrouter.ai", 429, "Too Many Requests", Message(), None)
        return _Response(
            _completion(
                content='{"status":"insufficient_support","answer":"No support.","citations":[]}'
            )
        )

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(
            api_key=SecretStr("secret-key"), transient_retries=1, cooldown_seconds=0
        ),
        opener=opener,
    )

    output = asyncio.run(adapter.generate(GenerationInput("prompt")))

    assert output.identity.mode is ProviderMode.LIVE
    assert calls == 2


def test_openrouter_adapter_uses_approved_model_identity_and_price_profile() -> None:
    captured: dict[str, object] = {}

    def opener(request: Request, _: float) -> _Response:
        raw_body = request.data
        assert isinstance(raw_body, bytes | bytearray)
        captured["body"] = json.loads(raw_body)
        return _Response(
            _completion(
                content='{"status":"insufficient_support","answer":"No support.","citations":[]}'
            )
        )

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(
            api_key=SecretStr("secret-key"),
            model="z-ai/glm-5.3-flash",
            reasoning_effort=None,
        ),
        opener=opener,
    )

    output = asyncio.run(adapter.generate(GenerationInput("prompt-body")))

    assert output.identity.name == "openrouter/z-ai/glm-5.3-flash"
    assert output.identity.revision == "glm-5.3-flash-2026-08-26"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "z-ai/glm-5.3-flash"
    assert "reasoning" not in body
    assert body["provider"] == {
        "zdr": True,
        "data_collection": "deny",
        "allow_fallbacks": False,
        "require_parameters": True,
        "sort": "price",
        "max_price": {"prompt": 0.45, "completion": 1.50},
    }


def test_openrouter_adapter_can_pin_one_provider_without_fallback() -> None:
    captured: dict[str, object] = {}

    def opener(request: Request, _: float) -> _Response:
        raw_body = request.data
        assert isinstance(raw_body, bytes | bytearray)
        captured["body"] = json.loads(raw_body)
        return _Response(
            _completion(
                content='{"status":"insufficient_support","answer":"No support.","citations":[]}'
            )
        )

    adapter = OpenRouterGenerationAdapter(
        OpenRouterGenerationConfig(
            api_key=SecretStr("secret-key"),
            model="deepseek/deepseek-v4-flash-0731",
            provider_only=("DeepInfra",),
            reasoning_effort=None,
        ),
        opener=opener,
    )

    asyncio.run(adapter.generate(GenerationInput("prompt-body")))

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["provider"] == {
        "zdr": True,
        "data_collection": "deny",
        "allow_fallbacks": False,
        "require_parameters": True,
        "max_price": {"prompt": 0.08, "completion": 0.20},
        "only": ["DeepInfra"],
    }


def test_openrouter_adapter_rejects_ambiguous_or_invalid_provider_routes() -> None:
    with pytest.raises(OpenRouterGenerationError) as conflict:
        OpenRouterGenerationConfig(
            api_key=SecretStr("secret-key"),
            provider_only=("DeepInfra",),
            provider_order=("Relace",),
        )
    assert conflict.value.code is OpenRouterGenerationErrorCode.REQUEST_FAILED

    with pytest.raises(OpenRouterGenerationError) as invalid:
        OpenRouterGenerationConfig(
            api_key=SecretStr("secret-key"),
            provider_only=("../secret",),
        )
    assert invalid.value.code is OpenRouterGenerationErrorCode.REQUEST_FAILED
