"""Framework-free ports and use case for declared corpus ingestion."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol, cast, runtime_checkable

from evalgate.application.ports import EmbeddingPort
from evalgate.domain.corpus import (
    CorpusChunk,
    DeclaredCorpus,
    IngestionError,
    IngestionErrorCode,
    IngestionReport,
)
from evalgate.domain.providers import ProviderMode


@runtime_checkable
class CorpusRepositoryPort(Protocol):
    """Persist one immutable corpus/index graph atomically."""

    def ingest(
        self,
        *,
        corpus: DeclaredCorpus,
        chunks: Sequence[CorpusChunk],
        vectors: Sequence[tuple[float, ...]],
        chunking_version: str,
        chunking_policy_sha256: str,
        lexical_config_sha256: str,
        embedding_model: str,
        embedding_revision: str,
        embedding_checksum: str,
        embedding_dimension: int,
    ) -> IngestionReport: ...

    def precheck(
        self,
        *,
        corpus: DeclaredCorpus,
        chunks: Sequence[CorpusChunk],
        chunking_version: str,
        chunking_policy_sha256: str,
        lexical_config_sha256: str,
        embedding_model: str,
        embedding_revision: str,
        embedding_checksum: str,
        embedding_dimension: int,
    ) -> IngestionReport | None: ...


async def ingest_declared_corpus(
    *,
    corpus: DeclaredCorpus,
    chunks: Sequence[CorpusChunk],
    embedding: EmbeddingPort,
    repository: CorpusRepositoryPort,
    chunking_version: str,
    chunking_policy_sha256: str,
    lexical_config_sha256: str,
) -> IngestionReport:
    """Embed reviewed chunks through the reference port then persist exactly once."""

    from evalgate.domain.providers import EmbeddingInput, EmbeddingRole

    if embedding.identity.mode is not ProviderMode.REFERENCE or embedding.dimension != 384:
        raise IngestionError(
            IngestionErrorCode.REFERENCE_EMBEDDING_INVALID,
            "declared corpus ingestion requires the reference embedding provider",
        )
    embedding_model = getattr(embedding, "model", None)
    embedding_revision = getattr(embedding, "revision", None)
    embedding_checksum = getattr(embedding, "checksum", None)
    if not all(
        isinstance(value, str) and value
        for value in (embedding_model, embedding_revision, embedding_checksum)
    ):
        raise IngestionError(
            IngestionErrorCode.REFERENCE_EMBEDDING_INVALID,
            "reference embedding identity is unavailable",
        )
    embedding_model = cast(str, embedding_model)
    embedding_revision = cast(str, embedding_revision)
    embedding_checksum = cast(str, embedding_checksum)
    preexisting = repository.precheck(
        corpus=corpus,
        chunks=chunks,
        chunking_version=chunking_version,
        chunking_policy_sha256=chunking_policy_sha256,
        lexical_config_sha256=lexical_config_sha256,
        embedding_model=embedding_model,
        embedding_revision=embedding_revision,
        embedding_checksum=embedding_checksum,
        embedding_dimension=embedding.dimension,
    )
    if preexisting is not None:
        return preexisting
    try:
        embedded = await embedding.embed(
            tuple(
                EmbeddingInput(text=chunk.content, role=EmbeddingRole.DOCUMENT) for chunk in chunks
            )
        )
    except IngestionError:
        raise
    except Exception as error:
        raise IngestionError(
            IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
            "reference embedding provider is unavailable",
        ) from error
    if len(embedded) != len(chunks) or any(
        vector.identity != embedding.identity
        or len(vector.values) != 384
        or any(not math.isfinite(value) for value in vector.values)
        for vector in embedded
    ):
        raise IngestionError(
            IngestionErrorCode.REFERENCE_EMBEDDING_INVALID,
            "reference embedding provider returned an invalid vector batch",
        )
    return repository.ingest(
        corpus=corpus,
        chunks=chunks,
        vectors=tuple(vector.values for vector in embedded),
        chunking_version=chunking_version,
        chunking_policy_sha256=chunking_policy_sha256,
        lexical_config_sha256=lexical_config_sha256,
        embedding_model=embedding_model,
        embedding_revision=embedding_revision,
        embedding_checksum=embedding_checksum,
        embedding_dimension=embedding.dimension,
    )
