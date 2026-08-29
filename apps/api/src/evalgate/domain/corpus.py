"""Immutable values used by the governed corpus ingestion flow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class IngestionErrorCode(StrEnum):
    """Non-sensitive failure categories exposed by the local admin command."""

    DECLARED_CORPUS_NOT_FOUND = "ingestion.declared_corpus_not_found"
    MANIFEST_INVALID = "ingestion.manifest_invalid"
    CORPUS_INVALID = "ingestion.corpus_invalid"
    REFERENCE_EMBEDDING_UNAVAILABLE = "ingestion.reference_embedding_unavailable"
    REFERENCE_EMBEDDING_INVALID = "ingestion.reference_embedding_invalid"
    PERSISTENCE_FAILED = "ingestion.persistence_failed"
    INGESTION_NOT_PERMITTED = "ingestion.not_permitted"


class IngestionError(RuntimeError):
    """Typed ingestion error whose message deliberately contains no corpus text or paths."""

    def __init__(self, code: IngestionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    """One validated immutable source document, before chunking."""

    source_key: str
    title: str
    license_id: str
    provenance: str
    content: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class CorpusChunk:
    """A deterministic chunk retaining offsets into normalized source content."""

    document_id: UUID
    source_key: str
    ordinal: int
    section_key: str
    source_start: int
    source_end: int
    content: str
    content_sha256: str
    token_count: int


@dataclass(frozen=True, slots=True)
class DeclaredCorpus:
    """A reviewed bundled corpus selected by its immutable public identity."""

    corpus_key: str
    version: str
    manifest_sha256: str
    documents: tuple[CorpusDocument, ...]


@dataclass(frozen=True, slots=True)
class IngestionReport:
    """Structured local-admin result without raw source or embedding content."""

    corpus_version_id: UUID
    index_version_id: UUID
    corpus_key: str
    corpus_version: str
    document_count: int
    chunk_count: int
    status: str
