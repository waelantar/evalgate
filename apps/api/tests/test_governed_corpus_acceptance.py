"""EG-004 acceptance tests for the closed, reproducible corpus boundary."""

from __future__ import annotations

import asyncio
import json
import sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import evalgate.adapters.bundled_corpus as bundled
from evalgate.adapters.bundled_corpus import (
    chunk_declared_corpus,
    corpus_version_id,
    document_id,
    load_declared_corpus_by_key,
)
from evalgate.adapters.fastembed_reference import FastEmbedReferenceEmbedding
from evalgate.adapters.reference_embedding import VerifiedReferenceSnapshot
from evalgate.application.ingestion import CorpusRepositoryPort, ingest_declared_corpus
from evalgate.application.provider_configuration import EmbeddingMode, GenerationMode
from evalgate.config import Settings
from evalgate.domain.corpus import (
    CorpusDocument,
    DeclaredCorpus,
    IngestionError,
    IngestionErrorCode,
)
from evalgate.domain.providers import (
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)
from evalgate.entrypoints.ingestion import ingest


class _CountingTokenizer:
    def token_count(self, texts: list[str]) -> int:
        return len(texts[0].split())


class _ReferenceEmbedding:
    identity = ProviderIdentity(ProviderMode.REFERENCE, "reviewed-runtime", "r1")
    dimension = 384
    model = "reviewed-runtime"
    revision = "r1"
    checksum = "c" * 64

    async def embed(self, inputs: Any) -> tuple[EmbeddingVector, ...]:
        return tuple(EmbeddingVector(values=(0.0,) * 384, identity=self.identity) for _ in inputs)


class _CapturingRepository:
    def __init__(self) -> None:
        self.arguments: dict[str, object] = {}

    def ingest(self, **kwargs: object) -> SimpleNamespace:
        self.arguments = kwargs
        return SimpleNamespace()

    def precheck(self, **kwargs: object) -> SimpleNamespace | None:
        self.arguments = kwargs
        return None


def _error_code(callable_: Any) -> IngestionErrorCode:
    with pytest.raises(IngestionError) as captured:
        callable_()
    return captured.value.code


def test_manifest_is_closed_and_corpus_is_exactly_declared() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")

    assert corpus.corpus_key == "northstar-operations"
    assert corpus.version == "1.0.0"
    assert len(corpus.documents) == 20
    assert all(document.license_id == "CC0-1.0" for document in corpus.documents)
    assert all(document.provenance.startswith("Original") for document in corpus.documents)


def test_manifest_unknown_field_and_path_escape_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(bundled.DECLARED_CORPORA[("northstar-operations", "1.0.0")])
    original = json.loads(source.read_text(encoding="utf-8"))
    manifest = tmp_path / "manifest.json"
    original["unexpected"] = True
    manifest.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setitem(bundled.DECLARED_CORPORA, ("northstar-operations", "1.0.0"), manifest)
    assert _error_code(lambda: load_declared_corpus_by_key("northstar-operations")) == (
        IngestionErrorCode.MANIFEST_INVALID
    )
    original.pop("unexpected")
    original["documents"][0]["path"] = "documents/../../outside.md"
    manifest.write_text(json.dumps(original), encoding="utf-8")
    assert _error_code(lambda: load_declared_corpus_by_key("northstar-operations")) == (
        IngestionErrorCode.MANIFEST_INVALID
    )


def test_declared_northstar_document_and_chunk_bounds_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path(bundled.DECLARED_CORPORA[("northstar-operations", "1.0.0")])
    manifest_data = json.loads(source.read_text(encoding="utf-8"))
    manifest_data["documents"] = manifest_data["documents"][:14]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    monkeypatch.setitem(bundled.DECLARED_CORPORA, ("northstar-operations", "1.0.0"), manifest)
    assert _error_code(lambda: load_declared_corpus_by_key("northstar-operations")) == (
        IngestionErrorCode.MANIFEST_INVALID
    )

    content = "## Only section\ncontent\n"
    document = CorpusDocument(
        "bounded-doc",
        "Bounded doc",
        "CC0-1.0",
        "Original fictional test corpus",
        content,
        sha256(content.encode()).hexdigest(),
    )
    corpus = DeclaredCorpus("northstar-operations", "test", "e" * 64, (document,))
    assert _error_code(lambda: chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer())) == (
        IngestionErrorCode.CORPUS_INVALID
    )


def test_normalization_hashes_and_ids_are_stable() -> None:
    raw = "## Caf\u00e9\r\nA\r\n\r\n".encode("utf-8")
    normalized = bundled._normalized_text(raw)
    assert normalized == "## Caf\u00e9\nA\n"
    document = CorpusDocument(
        source_key="normalization-proof",
        title="Normalization proof",
        license_id="CC0-1.0",
        provenance="Original fictional test corpus",
        content=normalized,
        content_sha256=sha256(normalized.encode()).hexdigest(),
    )
    corpus = DeclaredCorpus("test-corpus", "1", "a" * 64, (document,))
    assert corpus_version_id(corpus) == corpus_version_id(corpus)
    assert document_id(corpus, document) == document_id(corpus, document)
    chunks = chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer()).chunks
    assert chunks[0].content == normalized[chunks[0].source_start : chunks[0].source_end]


def test_duplicate_h2_slug_and_token_limit_are_rejected() -> None:
    content = "## Same\nfirst\n## Same\nsecond\n"
    document = CorpusDocument(
        "slug-proof",
        "Slug proof",
        "CC0-1.0",
        "Original fictional test corpus",
        content,
        sha256(content.encode()).hexdigest(),
    )
    corpus = DeclaredCorpus("test-corpus", "1", "b" * 64, (document,))
    assert _error_code(lambda: chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer())) == (
        IngestionErrorCode.CORPUS_INVALID
    )

    class _TooManyTokens:
        def token_count(self, texts: list[str]) -> int:
            return 513

    unique_content = "## Unique section\ncontent\n"
    unique_document = CorpusDocument(
        "token-proof",
        "Token proof",
        "CC0-1.0",
        "Original fictional test corpus",
        unique_content,
        sha256(unique_content.encode()).hexdigest(),
    )
    unique_corpus = DeclaredCorpus("test-corpus", "1", "c" * 64, (unique_document,))
    assert _error_code(
        lambda: chunk_declared_corpus(unique_corpus, tokenizer=_TooManyTokens())
    ) == (IngestionErrorCode.CORPUS_INVALID)


def test_chunk_offsets_sections_and_actual_token_counter_contract() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunks = chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer()).chunks
    documents = {document.source_key: document for document in corpus.documents}
    assert len(chunks) >= 150
    assert len(chunks) <= 400
    assert len({chunk.section_key for chunk in chunks}) == len(chunks)
    assert all(chunk.section_key.isascii() for chunk in chunks)
    assert all(0 < chunk.token_count <= 512 for chunk in chunks)
    assert all(
        documents[chunk.source_key].content[chunk.source_start : chunk.source_end] == chunk.content
        for chunk in chunks
    )


def test_application_uses_verified_adapter_identity_not_caller_metadata() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunks = chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer()).chunks[:1]
    repository = _CapturingRepository()
    embedding = _ReferenceEmbedding()
    asyncio.run(
        ingest_declared_corpus(
            corpus=corpus,
            chunks=chunks,
            embedding=embedding,
            repository=cast(CorpusRepositoryPort, repository),
            chunking_version="policy-v1",
            chunking_policy_sha256="a" * 64,
            lexical_config_sha256="b" * 64,
        )
    )
    assert repository.arguments["embedding_model"] == embedding.model
    assert repository.arguments["embedding_revision"] == embedding.revision
    assert repository.arguments["embedding_checksum"] == embedding.checksum


def test_application_rejects_runtime_failure_and_never_leaks_chunk_text() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunk = chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer()).chunks[0]

    class _BrokenEmbedding(_ReferenceEmbedding):
        async def embed(self, inputs: Any) -> tuple[EmbeddingVector, ...]:
            raise RuntimeError(chunk.content)

    with pytest.raises(IngestionError) as captured:
        asyncio.run(
            ingest_declared_corpus(
                corpus=corpus,
                chunks=(chunk,),
                embedding=_BrokenEmbedding(),
                repository=cast(CorpusRepositoryPort, _CapturingRepository()),
                chunking_version="v1",
                chunking_policy_sha256="a" * 64,
                lexical_config_sha256="b" * 64,
            )
        )
    assert captured.value.code is IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE
    assert chunk.content not in str(captured.value)


def test_reference_adapter_uses_supported_logical_model_with_verified_runtime_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class _Runtime:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    manifest = Path(__file__).resolve().parents[3] / "contracts/manifests/reference-embedding.json"
    monkeypatch.setattr(
        "evalgate.adapters.fastembed_reference.verify_reference_snapshot",
        lambda **_: VerifiedReferenceSnapshot(
            path=tmp_path, identity="reviewed", runtime_revision="runtime-revision", dimension=384
        ),
    )
    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=_Runtime))
    adapter = FastEmbedReferenceEmbedding.from_verified_snapshot(
        manifest_path=manifest, snapshot_path=tmp_path
    )
    assert captured["model_name"] == "BAAI/bge-small-en-v1.5"
    assert captured["specific_model_path"] == str(tmp_path)
    assert captured["local_files_only"] is True
    assert captured["providers"] == ["CPUExecutionProvider"]
    assert adapter.revision == "runtime-revision"


def test_reference_adapter_redacts_nonfinite_values_and_runtime_errors() -> None:
    adapter = FastEmbedReferenceEmbedding(
        runtime=SimpleNamespace(embed=lambda _: iter(((float("nan"),) * 384,))),
        identity=ProviderIdentity(ProviderMode.REFERENCE, "runtime", "r1"),
        dimension=384,
        model="runtime",
        revision="r1",
        checksum="c" * 64,
    )
    with pytest.raises(IngestionError) as captured:
        asyncio.run(adapter.embed((cast(Any, SimpleNamespace(text="secret chunk text")),)))
    assert captured.value.code is IngestionErrorCode.REFERENCE_EMBEDDING_INVALID
    assert "secret chunk text" not in str(captured.value)


def test_reference_adapter_redacts_runtime_construction_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _BrokenRuntime:
        def __init__(self, **kwargs: object) -> None:
            del kwargs
            raise RuntimeError("sensitive runtime detail")

    manifest = Path(__file__).resolve().parents[3] / "contracts/manifests/reference-embedding.json"
    monkeypatch.setattr(
        "evalgate.adapters.fastembed_reference.verify_reference_snapshot",
        lambda **_: VerifiedReferenceSnapshot(
            path=tmp_path,
            identity="reviewed",
            runtime_revision="runtime-revision",
            dimension=384,
        ),
    )
    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=_BrokenRuntime))

    with pytest.raises(IngestionError) as captured:
        FastEmbedReferenceEmbedding.from_verified_snapshot(
            manifest_path=manifest,
            snapshot_path=tmp_path,
        )

    assert captured.value.code is IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE
    assert "sensitive runtime detail" not in str(captured.value)


def test_exact_precheck_skips_embedding_work() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunk = chunk_declared_corpus(corpus, tokenizer=_CountingTokenizer()).chunks[0]

    class _NoEmbedding(_ReferenceEmbedding):
        async def embed(self, inputs: Any) -> tuple[EmbeddingVector, ...]:
            raise AssertionError("exact repeat must not embed")

    expected = SimpleNamespace(status="already_present")

    class _ExistingRepository(_CapturingRepository):
        def precheck(self, **kwargs: object) -> SimpleNamespace:
            self.arguments = kwargs
            return expected

    repository = _ExistingRepository()
    result = asyncio.run(
        ingest_declared_corpus(
            corpus=corpus,
            chunks=(chunk,),
            embedding=_NoEmbedding(),
            repository=cast(CorpusRepositoryPort, repository),
            chunking_version="v1",
            chunking_policy_sha256="a" * 64,
            lexical_config_sha256="b" * 64,
        )
    )
    assert result.status == "already_present"


@pytest.mark.parametrize(
    ("environment", "embedding_mode", "expected"),
    [
        ("public", EmbeddingMode.REFERENCE, IngestionErrorCode.INGESTION_NOT_PERMITTED),
        ("local", EmbeddingMode.FIXTURE, IngestionErrorCode.INGESTION_NOT_PERMITTED),
    ],
)
def test_cli_ingestion_is_closed_to_public_or_fixture_modes(
    environment: str, embedding_mode: EmbeddingMode, expected: IngestionErrorCode
) -> None:
    settings = Settings(
        environment=environment,  # type: ignore[arg-type]
        embedding_mode=embedding_mode,
        generation_mode=GenerationMode.DISABLED,
        reference_embedding_snapshot="snapshot"
        if embedding_mode is EmbeddingMode.REFERENCE
        else None,
    )
    with pytest.raises(IngestionError) as captured:
        asyncio.run(ingest(corpus_key="northstar-operations", settings=settings))
    assert captured.value.code is expected


def test_cli_rejects_undeclared_corpus_before_any_runtime_construction() -> None:
    settings = Settings(
        embedding_mode=EmbeddingMode.REFERENCE,
        generation_mode=GenerationMode.DISABLED,
        reference_embedding_snapshot="snapshot",
    )
    with pytest.raises(IngestionError) as captured:
        asyncio.run(ingest(corpus_key="not-declared", settings=settings))
    assert captured.value.code is IngestionErrorCode.DECLARED_CORPUS_NOT_FOUND
