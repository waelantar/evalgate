"""Privacy and branch-selection tests for the independent ablation CLI."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from collections.abc import Sequence
from uuid import UUID

import pytest
from pydantic import SecretStr

from evalgate.application.search import MAX_QUERY_CODE_POINTS, normalize_query
from evalgate.config import Settings
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.domain.search import EvidenceChunk, IndexIdentity, RankedCandidate, RetrievalMode
from evalgate.entrypoints import retrieval_ablation

SHA = "a" * 64
INDEX_ID = UUID(int=1)
IDENTITY = ProviderIdentity(ProviderMode.REFERENCE, "reference", "r1")


class _Engine:
    async def dispose(self) -> None:
        return None


class _Embedding:
    identity = IDENTITY
    dimension = 384
    model = "model"
    revision = "r1"
    checksum = SHA

    def __init__(self) -> None:
        self.embed_calls = 0

    def token_count(self, texts: Sequence[str]) -> int:
        return 1

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        self.embed_calls += 1
        return (EmbeddingVector((1.0,) + (0.0,) * 383, self.identity),)


class _Repository:
    def __init__(self) -> None:
        self.lexical_calls = 0
        self.vector_calls = 0

    async def resolve_index(self, index_version: UUID) -> IndexIdentity | None:
        return IndexIdentity(
            index_version_id=INDEX_ID,
            index_key="index",
            chunking_version="h2-v1",
            chunking_policy_sha256=SHA,
            lexical_config_sha256=(
                "4434b9362573450f668ed0014f428e744d3a7cc30f4630ebafedb22708b7d786"
            ),
            embedding_model="model",
            embedding_revision="r1",
            embedding_checksum=SHA,
            embedding_dimension=384,
            corpus_version_id=UUID(int=2),
            corpus_key="corpus",
            corpus_version="1.0.0",
            corpus_manifest_sha256=SHA,
        )

    def _candidate(self) -> tuple[RankedCandidate, ...]:
        return (
            RankedCandidate(
                EvidenceChunk(
                    evidence_id=UUID(int=3),
                    document_id=UUID(int=4),
                    source_key="source",
                    title="Title",
                    license_id="CC0-1.0",
                    provenance="Original fictional corpus",
                    section_key="section",
                    source_start=0,
                    source_end=7,
                    content="private chunk sentinel",
                    content_sha256=SHA,
                ),
                1,
            ),
        )

    async def lexical_candidates(
        self, *, index_version: UUID, query: str, depth: int
    ) -> tuple[RankedCandidate, ...]:
        self.lexical_calls += 1
        return self._candidate()

    async def vector_candidates(
        self, *, index_version: UUID, embedding: tuple[float, ...], depth: int
    ) -> tuple[RankedCandidate, ...]:
        self.vector_calls += 1
        return self._candidate()


@pytest.mark.parametrize(
    ("mode", "lexical_calls", "vector_calls", "embed_calls"),
    [
        (RetrievalMode.LEXICAL, 1, 0, 0),
        (RetrievalMode.VECTOR, 0, 1, 1),
        (RetrievalMode.HYBRID, 1, 1, 1),
    ],
)
def test_selected_mode_disables_unused_retrieval_branch(
    monkeypatch: pytest.MonkeyPatch,
    mode: RetrievalMode,
    lexical_calls: int,
    vector_calls: int,
    embed_calls: int,
) -> None:
    repository = _Repository()
    embedding = _Embedding()
    monkeypatch.setattr(retrieval_ablation, "create_async_engine", lambda *a, **k: _Engine())
    monkeypatch.setattr(
        retrieval_ablation,
        "build_reference_retrieval",
        lambda **kwargs: (repository, embedding),
    )

    report = asyncio.run(
        retrieval_ablation.run_ablation(
            query="private query sentinel",
            index_version=INDEX_ID,
            modes=(mode,),
            warmups=0,
            repetitions=1,
            limit=1,
            settings=Settings(database_url=SecretStr("postgresql+psycopg://unused")),
        )
    )

    assert repository.lexical_calls == lexical_calls
    assert repository.vector_calls == vector_calls
    assert embedding.embed_calls == embed_calls
    serialized = json.dumps(report)
    assert "private query sentinel" not in serialized
    assert "private chunk sentinel" not in serialized
    assert set(report["modes"]) == {mode.value}


def test_main_reads_query_from_stdin_and_emits_content_free_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "stdin-only-query-sentinel"
    captured: dict[str, object] = {}

    async def fake_run(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"safe": True}

    monkeypatch.setattr(retrieval_ablation, "run_ablation", fake_run)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(marker))
    monkeypatch.setattr(
        sys,
        "argv",
        ["evalgate-retrieval-ablation", "--index-version", str(INDEX_ID), "--mode", "lexical"],
    )

    retrieval_ablation.main()

    output = capsys.readouterr()
    assert captured["query"] == marker
    assert captured["modes"] == (RetrievalMode.LEXICAL,)
    assert json.loads(output.out) == {"safe": True}
    assert marker not in output.out + output.err


def test_main_failure_is_content_free(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "failed-query-sentinel"

    async def fail(**kwargs: object) -> dict[str, object]:
        raise RuntimeError(marker)

    monkeypatch.setattr(retrieval_ablation, "run_ablation", fail)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(marker))
    monkeypatch.setattr(
        sys,
        "argv",
        ["evalgate-retrieval-ablation", "--index-version", str(INDEX_ID)],
    )

    with pytest.raises(SystemExit) as captured:
        retrieval_ablation.main()

    output = capsys.readouterr()
    assert captured.value.code == 1
    assert marker not in output.out + output.err


def test_main_bounds_stdin_before_application_rejects_oversized_query(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tail_marker = "unread-private-tail-sentinel"
    stream = io.StringIO("x" * (MAX_QUERY_CODE_POINTS + 1) + tail_marker)
    captured_query: list[str] = []

    async def validate_query(**kwargs: object) -> dict[str, object]:
        query = kwargs["query"]
        assert isinstance(query, str)
        captured_query.append(query)
        normalize_query(query)
        return {"unreachable": True}

    monkeypatch.setattr(retrieval_ablation, "run_ablation", validate_query)
    monkeypatch.setattr(sys, "stdin", stream)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evalgate-retrieval-ablation", "--index-version", str(INDEX_ID)],
    )

    with pytest.raises(SystemExit) as captured:
        retrieval_ablation.main()

    output = capsys.readouterr()
    assert captured.value.code == 1
    assert captured_query == ["x" * (MAX_QUERY_CODE_POINTS + 1)]
    assert tail_marker not in output.out + output.err
