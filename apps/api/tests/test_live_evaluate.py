"""Governed live-evaluation artifact tests without provider calls."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from pydantic import SecretStr

from evalgate.application.provider_configuration import (
    EmbeddingMode,
    GenerationMode,
    LiveProvider,
)
from evalgate.config import Settings
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    GenerationInput,
    GenerationOutput,
    GenerationUsage,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import HYBRID_RRF_V1, EvidenceChunk, IndexIdentity, RankedCandidate
from evalgate.entrypoints import live_evaluate

INDEX_ID = UUID("10000000-0000-0000-0000-000000000001")
CORPUS_ID = UUID("20000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("30000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000001")
SHA = "a" * 64
LIVE_IDENTITY = ProviderIdentity(ProviderMode.LIVE, "openrouter/deepseek", "test")


class _Engine:
    async def dispose(self) -> None:
        return None


class _Embedding:
    identity = ProviderIdentity(ProviderMode.REFERENCE, "reference", "test")
    dimension = 384
    model = "reference"
    revision = "test"
    checksum = SHA

    def token_count(self, texts: Sequence[str]) -> int:
        return sum(max(1, len(text.split())) for text in texts)

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        return tuple(EmbeddingVector((1.0,) + (0.0,) * 383, self.identity) for _ in inputs)


class _Repository:
    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        if index_version != INDEX_ID:
            return None
        return IndexIdentity(
            index_version_id=INDEX_ID,
            index_key="reviewed-index",
            chunking_version="h2-v1",
            chunking_policy_sha256=SHA,
            lexical_config_sha256=HYBRID_RRF_V1.lexical_config_sha256,
            embedding_model="reference",
            embedding_revision="test",
            embedding_checksum=SHA,
            embedding_dimension=384,
            corpus_version_id=CORPUS_ID,
            corpus_key="corpus",
            corpus_version="1.0.0",
            corpus_manifest_sha256="b" * 64,
        )

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        return (_candidate(),)

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        return (_candidate(),)


class _Generation:
    identity = LIVE_IDENTITY

    def __init__(self, text: str, cost: float) -> None:
        self._text = text
        self._cost = cost

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        return GenerationOutput(
            text=self._text,
            identity=self.identity,
            usage=GenerationUsage(10, 5, 15, self._cost),
        )


def _candidate() -> RankedCandidate:
    content = "Status ledger recovery evidence."
    return RankedCandidate(
        evidence=EvidenceChunk(
            evidence_id=EVIDENCE_ID,
            document_id=DOCUMENT_ID,
            source_key="status-ledger",
            title="Status Ledger",
            license_id="CC0-1.0",
            provenance="Original fictional corpus",
            section_key="recovery",
            source_start=0,
            source_end=len(content),
            content=content,
            content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        ),
        rank=1,
    )


def _dataset(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_version": "test-v1",
                "cases": [
                    {
                        "case_id": "case-1",
                        "split": "development",
                        "question": "How is recovery handled?",
                        "answerability": "answerable",
                        "relevant_evidence_ids": [str(EVIDENCE_ID)],
                        "supported_claims": ["status-ledger-recovery"],
                        "review_state": "reviewed",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _settings() -> Settings:
    return Settings(
        environment="ci",
        embedding_mode=EmbeddingMode.REFERENCE,
        generation_mode=GenerationMode.LIVE,
        reference_embedding_snapshot="snapshot",
        live_provider=LiveProvider.OPENROUTER,
        openrouter_api_key=SecretStr("private-key-marker"),
        openrouter_model="deepseek/deepseek-v4-flash",
        live_eval_budget_usd=4.60,
        live_eval_stop_usd=4.14,
    )


def test_live_generation_artifact_validates_and_redacts_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _dataset(dataset_path)
    answer = "Status ledger recovery is required."
    generation = _Generation(
        json.dumps(
            {
                "status": "answered",
                "answer": answer,
                "citations": [
                    {
                        "answer_start": 0,
                        "answer_end": len(answer),
                        "evidence_ids": [str(EVIDENCE_ID)],
                    }
                ],
            }
        ),
        0.001,
    )
    judge = _Generation(json.dumps({"decision": "pass", "reason_code": "supported_answer"}), 0.001)
    monkeypatch.setattr(live_evaluate, "create_async_engine", lambda *_, **__: _Engine())
    monkeypatch.setattr(
        live_evaluate, "build_reference_retrieval", lambda **_: (_Repository(), _Embedding())
    )

    artifact = asyncio.run(
        live_evaluate.build_live_generation_artifact(
            dataset_path=dataset_path,
            index_version=INDEX_ID,
            settings=_settings(),
            generation=generation,
            judge=judge,
            repetitions=2,
            max_cases=None,
        )
    )
    schema = json.loads(
        (Path(__file__).parents[3] / "contracts/evaluation/artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(artifact)

    encoded = json.dumps(artifact)
    assert artifact["run"]["mode"] == "generation"
    assert artifact["metrics"]["repetition_count"] == 2.0
    assert artifact["metrics"]["human_judge_agreement"] == 1.0
    assert artifact["metrics"]["total_cost_usd"] == 0.004
    assert "Status ledger recovery is required" not in encoded
    assert "private-key-marker" not in encoded


def test_live_generation_artifact_records_malformed_answer_without_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _dataset(dataset_path)
    answer = "Status ledger recovery is required."
    generation = _Generation(
        json.dumps(
            {
                "status": "answered",
                "answer": answer,
                "citations": [
                    {
                        "answer_start": 0,
                        "answer_end": len(answer) + 1,
                        "evidence_ids": [str(EVIDENCE_ID)],
                    }
                ],
            }
        ),
        0.001,
    )
    judge = _Generation(json.dumps({"decision": "pass", "reason_code": "supported_answer"}), 0.0)
    monkeypatch.setattr(live_evaluate, "create_async_engine", lambda *_, **__: _Engine())
    monkeypatch.setattr(
        live_evaluate, "build_reference_retrieval", lambda **_: (_Repository(), _Embedding())
    )

    artifact = asyncio.run(
        live_evaluate.build_live_generation_artifact(
            dataset_path=dataset_path,
            index_version=INDEX_ID,
            settings=_settings(),
            generation=generation,
            judge=judge,
            repetitions=1,
            max_cases=None,
        )
    )
    schema = json.loads(
        (Path(__file__).parents[3] / "contracts/evaluation/artifact.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(artifact)

    repetition = artifact["cases"][0]["repetitions"][0]
    assert repetition["answer_status"] == "malformed_output"
    assert repetition["retrieved_evidence_ids"] == [str(EVIDENCE_ID)]
    assert repetition["citation_evidence_ids"] == []
    assert repetition["generation_usage"]["cost_usd"] == 0.001
    assert repetition["judge_decision"] == "fail"
    assert repetition["judge_reason_code"] == "malformed_output"
    assert repetition["passed"] is False
    assert artifact["metrics"]["human_pass_rate"] == 0.0
    assert artifact["metrics"]["judge_evaluated_count"] == 0.0


def test_live_generation_artifact_stops_at_approved_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "dataset.json"
    _dataset(dataset_path)
    answer = "Status ledger recovery is required."
    generation = _Generation(
        json.dumps(
            {
                "status": "answered",
                "answer": answer,
                "citations": [
                    {
                        "answer_start": 0,
                        "answer_end": len(answer),
                        "evidence_ids": [str(EVIDENCE_ID)],
                    }
                ],
            }
        ),
        5.0,
    )
    judge = _Generation(json.dumps({"decision": "pass", "reason_code": "supported_answer"}), 0.0)
    monkeypatch.setattr(live_evaluate, "create_async_engine", lambda *_, **__: _Engine())
    monkeypatch.setattr(
        live_evaluate, "build_reference_retrieval", lambda **_: (_Repository(), _Embedding())
    )

    try:
        asyncio.run(
            live_evaluate.build_live_generation_artifact(
                dataset_path=dataset_path,
                index_version=INDEX_ID,
                settings=_settings(),
                generation=generation,
                judge=judge,
                repetitions=1,
                max_cases=None,
            )
        )
    except ValueError as error:
        assert "stop limit" in str(error)
    else:
        raise AssertionError("live evaluation accepted an over-budget run")
