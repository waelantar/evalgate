"""Closed-input validation and deterministic chunking for the bundled corpus."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from evalgate.domain.corpus import (
    CorpusChunk,
    CorpusDocument,
    DeclaredCorpus,
    IngestionError,
    IngestionErrorCode,
)

CORPUS_ROOT = Path(__file__).resolve().parents[5] / "data" / "corpus"
MANIFEST_ROOT = Path(__file__).resolve().parents[5] / "data" / "manifests"
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
DECLARED_CORPORA = {
    ("northstar-operations", "1.0.0"): MANIFEST_ROOT / "northstar-operations-v1.json",
}
CHUNKING_VERSION = "northstar-heading-v1"
LEXICAL_CONFIGURATION = "pg_catalog.simple"
POLICY_MANIFEST = REPOSITORY_ROOT / "contracts" / "manifests" / "northstar-index-policy-v1.json"
LEXICAL_CONFIG_SHA256 = sha256(b"postgresql-tsvector:pg_catalog.simple").hexdigest()
_HEADING = re.compile(r"(?m)^##\s+(.+?)\s*$")
_CC0_NORMALIZED_SHA256 = "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"
_EXPECTED_INDEX_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "chunking_version": "northstar-heading-v1",
    "normalization": "strict UTF-8; NFC; CRLF/CR to LF; exactly one terminal LF",
    "offset_unit": "Python Unicode code-point index into normalized source",
    "chunking": "each H2 begins one chunk through before the next H2; H3 remains in its parent",
    "section_key": "source_key plus unique ASCII heading slug",
    "token_count": "FastEmbed tokenizer count; each chunk is at most 512 tokens",
    "lexical_regconfig": "pg_catalog.simple",
}


@dataclass(frozen=True, slots=True)
class ChunkedCorpus:
    """Validated corpus plus its deterministic, reviewed chunk materialization."""

    corpus: DeclaredCorpus
    chunks: tuple[CorpusChunk, ...]


class TokenCounter(Protocol):
    def token_count(self, texts: list[str]) -> int: ...


def _error(code: IngestionErrorCode, message: str) -> IngestionError:
    return IngestionError(code, message)


def _normalized_text(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus document is not UTF-8") from error
    if text.startswith("\ufeff"):
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus document contains a UTF-8 BOM")
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return normalized.rstrip("\n") + "\n"


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _load_index_policy_sha256(path: Path = POLICY_MANIFEST) -> str:
    try:
        policy: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID,
            "index policy manifest could not be read",
        ) from error
    if policy != _EXPECTED_INDEX_POLICY:
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "index policy manifest is invalid")
    return sha256(_canonical_json_bytes(policy)).hexdigest()


CHUNKING_POLICY_SHA256 = _load_index_policy_sha256()


def _validate_manifest(manifest: object) -> dict[str, object]:
    schema_path = REPOSITORY_ROOT / "contracts" / "manifests" / "corpus.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = tuple(Draft202012Validator(schema).iter_errors(manifest))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID, "corpus manifest schema is unavailable"
        ) from error
    if errors or not isinstance(manifest, dict):
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "declared corpus manifest is invalid")
    return manifest


def _validate_corpus_layout(manifest_paths: set[Path]) -> None:
    declared = {(CORPUS_ROOT / path).resolve() for path in manifest_paths}
    actual = {path.resolve() for path in (CORPUS_ROOT / "documents").rglob("*") if path.is_file()}
    if declared != actual:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID,
            "manifest document set does not match bundled corpus",
        )
    license_path = CORPUS_ROOT / "CC0-1.0.txt"
    try:
        if (
            sha256(_normalized_text(license_path.read_bytes()).encode("utf-8")).hexdigest()
            != _CC0_NORMALIZED_SHA256
        ):
            raise _error(
                IngestionErrorCode.CORPUS_INVALID, "approved corpus license text does not match"
            )
    except OSError as error:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID, "approved corpus license text is unavailable"
        ) from error


def _safe_document_path(value: object) -> Path:
    if not isinstance(value, str) or not value.startswith("documents/"):
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "manifest document path is invalid")
    candidate = (CORPUS_ROOT / value).resolve()
    documents_root = (CORPUS_ROOT / "documents").resolve()
    try:
        candidate.relative_to(documents_root)
    except ValueError as error:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID, "manifest document path escapes corpus"
        ) from error
    if candidate.suffix != ".md":
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "manifest document type is invalid")
    return candidate


def load_declared_corpus(*, corpus_key: str, version: str) -> DeclaredCorpus:
    """Load only the reviewed bundled corpus selected by exact key and version."""

    manifest_path = DECLARED_CORPORA.get((corpus_key, version))
    if manifest_path is None:
        raise _error(IngestionErrorCode.DECLARED_CORPUS_NOT_FOUND, "corpus is not declared")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID, "declared corpus manifest could not be read"
        ) from error
    manifest = _validate_manifest(manifest)
    if (
        manifest.get("schema_version") != "1.0"
        or manifest.get("corpus_key") != corpus_key
        or manifest.get("version") != version
        or manifest.get("license") != "CC0-1.0"
    ):
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "declared corpus identity is invalid")
    records = manifest.get("documents")
    if not isinstance(records, list) or not 15 <= len(records) <= 25:
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "declared corpus has no documents")
    documents: list[CorpusDocument] = []
    manifest_paths: set[Path] = set()
    source_paths: set[Path] = set()
    source_keys: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise _error(IngestionErrorCode.MANIFEST_INVALID, "manifest document record is invalid")
        source_key = record.get("source_key")
        title = record.get("title")
        license_id = record.get("license")
        provenance = record.get("provenance")
        expected_sha256 = record.get("sha256")
        if (
            not all(
                isinstance(item, str) and item
                for item in (source_key, title, license_id, provenance)
            )
            or license_id != "CC0-1.0"
            or not isinstance(expected_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
            or record.get("media_type") != "text/markdown"
            or source_key in source_keys
        ):
            raise _error(
                IngestionErrorCode.MANIFEST_INVALID, "manifest document metadata is invalid"
            )
        assert isinstance(source_key, str)
        assert isinstance(title, str)
        assert isinstance(provenance, str)
        source_keys.add(source_key)
        path = _safe_document_path(record.get("path"))
        if path in source_paths:
            raise _error(
                IngestionErrorCode.MANIFEST_INVALID, "manifest document path is duplicated"
            )
        source_paths.add(path)
        manifest_paths.add(path.relative_to(CORPUS_ROOT))
        try:
            content = _normalized_text(path.read_bytes())
        except OSError as error:
            raise _error(
                IngestionErrorCode.CORPUS_INVALID, "declared corpus document could not be read"
            ) from error
        actual_sha256 = sha256(content.encode("utf-8")).hexdigest()
        if actual_sha256 != expected_sha256:
            raise _error(
                IngestionErrorCode.CORPUS_INVALID, "declared corpus document hash mismatch"
            )
        documents.append(
            CorpusDocument(
                source_key=source_key,
                title=title,
                license_id=license_id,
                provenance=provenance,
                content=content,
                content_sha256=actual_sha256,
            )
        )
    _validate_corpus_layout(manifest_paths)
    return DeclaredCorpus(
        corpus_key=corpus_key,
        version=version,
        manifest_sha256=sha256(_canonical_json_bytes(manifest)).hexdigest(),
        documents=tuple(documents),
    )


def load_declared_corpus_by_key(corpus_key: str) -> DeclaredCorpus:
    """Resolve one registered bundled corpus without accepting caller-controlled paths."""

    matches = [version for key, version in DECLARED_CORPORA if key == corpus_key]
    if len(matches) != 1:
        raise _error(IngestionErrorCode.DECLARED_CORPUS_NOT_FOUND, "corpus is not declared")
    return load_declared_corpus(corpus_key=corpus_key, version=matches[0])


def corpus_version_id(corpus: DeclaredCorpus) -> UUID:
    """Derive a stable database identity from immutable corpus evidence."""

    return uuid5(
        NAMESPACE_URL,
        f"urn:evalgate:corpus:{corpus.corpus_key}:{corpus.version}:{corpus.manifest_sha256}",
    )


def document_id(corpus: DeclaredCorpus, document: CorpusDocument) -> UUID:
    """Derive a stable document identity within one immutable corpus version."""

    return uuid5(
        corpus_version_id(corpus), f"document:{document.source_key}:{document.content_sha256}"
    )


def chunk_declared_corpus(corpus: DeclaredCorpus, *, tokenizer: TokenCounter) -> ChunkedCorpus:
    """Chunk H2 source sections with reconstructive normalized-source offsets."""

    chunks: list[CorpusChunk] = []
    for document in corpus.documents:
        matches = tuple(_HEADING.finditer(document.content))
        if not matches:
            raise _error(
                IngestionErrorCode.CORPUS_INVALID, "corpus document has no approved sections"
            )
        doc_id = document_id(corpus, document)
        used_slugs: set[str] = set()
        for ordinal, match in enumerate(matches):
            end = (
                matches[ordinal + 1].start()
                if ordinal + 1 < len(matches)
                else len(document.content)
            )
            content = document.content[match.start() : end]
            source_start = match.start()
            source_end = end
            if not content.strip():
                raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus section is empty")
            slug = _ascii_slug(match.group(1))
            if slug in used_slugs:
                raise _error(
                    IngestionErrorCode.CORPUS_INVALID, "corpus section heading is not unique"
                )
            used_slugs.add(slug)
            try:
                token_count = int(tokenizer.token_count([content]))
            except Exception as error:
                raise _error(
                    IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                    "reference tokenizer is unavailable",
                ) from error
            if token_count < 1 or token_count > 512:
                raise _error(
                    IngestionErrorCode.CORPUS_INVALID, "corpus section exceeds approved token limit"
                )
            chunks.append(
                CorpusChunk(
                    document_id=doc_id,
                    source_key=document.source_key,
                    ordinal=ordinal,
                    section_key=f"{document.source_key}:{slug}",
                    source_start=source_start,
                    source_end=source_end,
                    content=content,
                    content_sha256=sha256(content.encode("utf-8")).hexdigest(),
                    token_count=token_count,
                )
            )
    if corpus.corpus_key == "northstar-operations" and not 150 <= len(chunks) <= 400:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID,
            "declared corpus does not meet the reviewed chunk-count bounds",
        )
    return ChunkedCorpus(corpus=corpus, chunks=tuple(chunks))


def _ascii_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower(),
    ).strip("-")
    if not slug:
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus section heading has no ASCII slug")
    return slug
