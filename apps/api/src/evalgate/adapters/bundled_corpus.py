"""Closed-input validation and deterministic chunking for registered bundled corpora."""

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

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
CORPUS_ROOT = REPOSITORY_ROOT / "data" / "corpus"
THIRD_PARTY_ROOT = REPOSITORY_ROOT / "data" / "third_party"
MANIFEST_ROOT = REPOSITORY_ROOT / "data" / "manifests"
CHUNKING_VERSION = "northstar-heading-v1"
KUBERNETES_DEBUG_CHUNKING_VERSION = "kubernetes-debug-heading-v1"
LEXICAL_CONFIGURATION = "pg_catalog.simple"
POLICY_MANIFEST = REPOSITORY_ROOT / "contracts" / "manifests" / "northstar-index-policy-v1.json"
KUBERNETES_DEBUG_POLICY_MANIFEST = (
    REPOSITORY_ROOT / "contracts" / "manifests" / "kubernetes-debug-index-policy-v1.json"
)
LEXICAL_CONFIG_SHA256 = sha256(b"postgresql-tsvector:pg_catalog.simple").hexdigest()
_HEADING_H2 = re.compile(r"(?m)^##\s+(.+?)\s*$")
_HEADING_H2_H3 = re.compile(r"(?m)^#{2,3}\s+(.+?)\s*$")
_CC0_NORMALIZED_SHA256 = "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"
_CC_BY_4_NORMALIZED_SHA256 = "9e5f1b3c610b9c2da5c313bf81d577a7d1acec686bdb0384edefa6df0f90cd94"
_EXPECTED_NORTHSTAR_INDEX_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "chunking_version": "northstar-heading-v1",
    "normalization": "strict UTF-8; NFC; CRLF/CR to LF; exactly one terminal LF",
    "offset_unit": "Python Unicode code-point index into normalized source",
    "chunking": "each H2 begins one chunk through before the next H2; H3 remains in its parent",
    "section_key": "source_key plus unique ASCII heading slug",
    "token_count": "FastEmbed tokenizer count; each chunk is at most 512 tokens",
    "lexical_regconfig": "pg_catalog.simple",
}
_EXPECTED_KUBERNETES_DEBUG_INDEX_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "chunking_version": "kubernetes-debug-heading-v1",
    "normalization": "strict UTF-8; NFC; CRLF/CR to LF; exactly one terminal LF",
    "offset_unit": "Python Unicode code-point index into normalized source",
    "chunking": (
        "each H2 or H3 begins a semantic section; sections over 512 tokens split at "
        "blank-line paragraph boundaries into consecutive reconstructive parts; deeper headings "
        "remain in their parent"
    ),
    "section_key": (
        "source_key plus unique ASCII heading slug, with part-N suffix only for split sections"
    ),
    "token_count": "FastEmbed tokenizer count; each chunk is at most 512 tokens",
    "lexical_regconfig": "pg_catalog.simple",
}


@dataclass(frozen=True, slots=True)
class CorpusDefinition:
    manifest_path: Path
    root: Path
    license_id: str
    license_path: Path
    license_sha256: str
    min_documents: int
    max_documents: int
    min_chunks: int
    max_chunks: int
    heading_pattern: re.Pattern[str]
    chunking_version: str
    policy_manifest: Path
    expected_policy: dict[str, object]
    require_exact_layout: bool = True


CORPUS_DEFINITIONS: dict[tuple[str, str], CorpusDefinition] = {
    ("northstar-operations", "1.0.0"): CorpusDefinition(
        manifest_path=MANIFEST_ROOT / "northstar-operations-v1.json",
        root=CORPUS_ROOT,
        license_id="CC0-1.0",
        license_path=CORPUS_ROOT / "CC0-1.0.txt",
        license_sha256=_CC0_NORMALIZED_SHA256,
        min_documents=15,
        max_documents=25,
        min_chunks=150,
        max_chunks=400,
        heading_pattern=_HEADING_H2,
        chunking_version=CHUNKING_VERSION,
        policy_manifest=POLICY_MANIFEST,
        expected_policy=_EXPECTED_NORTHSTAR_INDEX_POLICY,
    ),
    ("kubernetes-debug-cluster", "1.0.0"): CorpusDefinition(
        manifest_path=MANIFEST_ROOT / "kubernetes-debug-cluster-v1.json",
        root=THIRD_PARTY_ROOT / "kubernetes-debug-cluster",
        license_id="CC-BY-4.0",
        license_path=THIRD_PARTY_ROOT / "kubernetes-debug-cluster" / "CC-BY-4.0.txt",
        license_sha256=_CC_BY_4_NORMALIZED_SHA256,
        min_documents=11,
        max_documents=11,
        min_chunks=55,
        max_chunks=110,
        heading_pattern=_HEADING_H2_H3,
        chunking_version=KUBERNETES_DEBUG_CHUNKING_VERSION,
        policy_manifest=KUBERNETES_DEBUG_POLICY_MANIFEST,
        expected_policy=_EXPECTED_KUBERNETES_DEBUG_INDEX_POLICY,
    ),
}
DECLARED_CORPORA: dict[tuple[str, str], Path] = {
    identity: definition.manifest_path for identity, definition in CORPUS_DEFINITIONS.items()
}
_DEFAULT_CHUNK_DEFINITION = CorpusDefinition(
    manifest_path=Path("in-memory-test-corpus.json"),
    root=Path("."),
    license_id="CC0-1.0",
    license_path=Path("CC0-1.0.txt"),
    license_sha256=_CC0_NORMALIZED_SHA256,
    min_documents=1,
    max_documents=100,
    min_chunks=1,
    max_chunks=1000,
    heading_pattern=_HEADING_H2,
    chunking_version=CHUNKING_VERSION,
    policy_manifest=POLICY_MANIFEST,
    expected_policy=_EXPECTED_NORTHSTAR_INDEX_POLICY,
    require_exact_layout=False,
)


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
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus document contains a UTF-8 BOM")
    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return normalized.rstrip("\n") + "\n"


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _load_index_policy_sha256(path: Path, expected: dict[str, object]) -> str:
    try:
        policy: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID,
            "index policy manifest could not be read",
        ) from error
    if policy != expected:
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "index policy manifest is invalid")
    return sha256(_canonical_json_bytes(policy)).hexdigest()


CHUNKING_POLICY_SHA256 = _load_index_policy_sha256(
    POLICY_MANIFEST, _EXPECTED_NORTHSTAR_INDEX_POLICY
)
KUBERNETES_DEBUG_CHUNKING_POLICY_SHA256 = _load_index_policy_sha256(
    KUBERNETES_DEBUG_POLICY_MANIFEST, _EXPECTED_KUBERNETES_DEBUG_INDEX_POLICY
)


def chunking_version_for_corpus(corpus_key: str) -> str:
    definition = _single_definition_for_key(corpus_key)
    return definition.chunking_version


def chunking_policy_sha256_for_corpus(corpus_key: str) -> str:
    definition = _single_definition_for_key(corpus_key)
    if definition.chunking_version == KUBERNETES_DEBUG_CHUNKING_VERSION:
        return KUBERNETES_DEBUG_CHUNKING_POLICY_SHA256
    return CHUNKING_POLICY_SHA256


def _single_definition_for_key(corpus_key: str) -> CorpusDefinition:
    matches = [
        definition
        for key, version in CORPUS_DEFINITIONS
        if key == corpus_key
        for definition in [CORPUS_DEFINITIONS[(key, version)]]
    ]
    if len(matches) != 1:
        return _DEFAULT_CHUNK_DEFINITION
    return matches[0]


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


def _validate_corpus_layout(definition: CorpusDefinition, manifest_paths: set[Path]) -> None:
    declared = {(definition.root / path).resolve() for path in manifest_paths}
    actual = {
        path.resolve() for path in (definition.root / "documents").rglob("*") if path.is_file()
    }
    if definition.require_exact_layout and declared != actual:
        raise _error(
            IngestionErrorCode.MANIFEST_INVALID,
            "manifest document set does not match bundled corpus",
        )
    try:
        license_hash = sha256(
            _normalized_text(definition.license_path.read_bytes()).encode("utf-8")
        ).hexdigest()
    except OSError as error:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID, "approved corpus license text is unavailable"
        ) from error
    if license_hash != definition.license_sha256:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID, "approved corpus license text does not match"
        )


def _safe_document_path(definition: CorpusDefinition, value: object) -> Path:
    if not isinstance(value, str) or not value.startswith("documents/"):
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "manifest document path is invalid")
    candidate = (definition.root / value).resolve()
    documents_root = (definition.root / "documents").resolve()
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
    """Load only a reviewed bundled corpus selected by exact key and version."""

    definition = CORPUS_DEFINITIONS.get((corpus_key, version))
    manifest_path = DECLARED_CORPORA.get((corpus_key, version))
    if definition is None or manifest_path is None:
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
        or manifest.get("license") != definition.license_id
    ):
        raise _error(IngestionErrorCode.MANIFEST_INVALID, "declared corpus identity is invalid")
    records = manifest.get("documents")
    if (
        not isinstance(records, list)
        or not definition.min_documents <= len(records) <= definition.max_documents
    ):
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
            or license_id != definition.license_id
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
        path = _safe_document_path(definition, record.get("path"))
        if path in source_paths:
            raise _error(
                IngestionErrorCode.MANIFEST_INVALID, "manifest document path is duplicated"
            )
        source_paths.add(path)
        manifest_paths.add(path.relative_to(definition.root))
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
    _validate_corpus_layout(definition, manifest_paths)
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
    """Chunk reviewed heading sections with reconstructive normalized-source offsets."""

    definition = _single_definition_for_key(corpus.corpus_key)
    chunks: list[CorpusChunk] = []
    for document in corpus.documents:
        matches = tuple(definition.heading_pattern.finditer(document.content))
        if not matches:
            raise _error(
                IngestionErrorCode.CORPUS_INVALID, "corpus document has no approved sections"
            )
        doc_id = document_id(corpus, document)
        used_slugs: set[str] = set()
        for ordinal, match in enumerate(matches):
            section_end = (
                matches[ordinal + 1].start()
                if ordinal + 1 < len(matches)
                else len(document.content)
            )
            if not document.content[match.start() : section_end].strip():
                raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus section is empty")
            slug = _ascii_slug(match.group(1))
            if slug in used_slugs:
                raise _error(
                    IngestionErrorCode.CORPUS_INVALID, "corpus section heading is not unique"
                )
            used_slugs.add(slug)
            parts = _section_parts(
                content=document.content,
                start=match.start(),
                end=section_end,
                tokenizer=tokenizer,
            )
            for part_number, (source_start, source_end, content, token_count) in enumerate(
                parts, start=1
            ):
                section_slug = slug if len(parts) == 1 else f"{slug}-part-{part_number}"
                chunks.append(
                    CorpusChunk(
                        document_id=doc_id,
                        source_key=document.source_key,
                        ordinal=len(chunks),
                        section_key=f"{document.source_key}:{section_slug}",
                        source_start=source_start,
                        source_end=source_end,
                        content=content,
                        content_sha256=sha256(content.encode("utf-8")).hexdigest(),
                        token_count=token_count,
                    )
                )
    if not definition.min_chunks <= len(chunks) <= definition.max_chunks:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID,
            "declared corpus does not meet the reviewed chunk-count bounds",
        )
    return ChunkedCorpus(corpus=corpus, chunks=tuple(chunks))


def _section_parts(
    *, content: str, start: int, end: int, tokenizer: TokenCounter
) -> tuple[tuple[int, int, str, int], ...]:
    section = content[start:end]
    token_count = _raw_token_count(tokenizer, section)
    if token_count <= 512:
        return ((start, end, section, token_count),)

    paragraphs: list[tuple[int, int]] = []
    cursor = start
    for match in re.finditer(r"\n\n+", section):
        split_end = start + match.end()
        paragraphs.append((cursor, split_end))
        cursor = split_end
    if cursor < end:
        paragraphs.append((cursor, end))

    parts: list[tuple[int, int, str, int]] = []
    part_start: int | None = None
    part_end: int | None = None
    part_text = ""
    part_tokens = 0
    for paragraph_start, paragraph_end in paragraphs:
        paragraph_text = content[paragraph_start:paragraph_end]
        paragraph_tokens = _token_count(tokenizer, paragraph_text)
        if paragraph_tokens > 512:
            raise _error(
                IngestionErrorCode.CORPUS_INVALID,
                "corpus paragraph exceeds approved token limit",
            )
        candidate = part_text + paragraph_text
        candidate_tokens = _raw_token_count(tokenizer, candidate) if part_text else paragraph_tokens
        if part_text and candidate_tokens > 512:
            assert part_start is not None and part_end is not None
            parts.append((part_start, part_end, part_text, part_tokens))
            part_start = paragraph_start
            part_text = paragraph_text
            part_end = paragraph_end
            part_tokens = paragraph_tokens
        else:
            part_start = paragraph_start if part_start is None else part_start
            part_text = candidate
            part_end = paragraph_end
            part_tokens = candidate_tokens
    if part_text:
        assert part_start is not None and part_end is not None
        parts.append((part_start, part_end, part_text, part_tokens))
    if not parts:
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus section is empty")
    return tuple(parts)


def _raw_token_count(tokenizer: TokenCounter, content: str) -> int:
    try:
        token_count = int(tokenizer.token_count([content]))
    except Exception as error:
        raise _error(
            IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
            "reference tokenizer is unavailable",
        ) from error
    if token_count < 1:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID,
            "corpus section exceeds approved token limit",
        )
    return token_count


def _token_count(tokenizer: TokenCounter, content: str) -> int:
    token_count = _raw_token_count(tokenizer, content)
    if token_count > 512:
        raise _error(
            IngestionErrorCode.CORPUS_INVALID,
            "corpus section exceeds approved token limit",
        )
    return token_count


def _ascii_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower(),
    ).strip("-")
    if not slug:
        raise _error(IngestionErrorCode.CORPUS_INVALID, "corpus section heading has no ASCII slug")
    return slug
