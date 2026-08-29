"""Local-admin command for closed-input governed corpus ingestion."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import create_engine

from evalgate.adapters.bundled_corpus import (
    CHUNKING_POLICY_SHA256,
    CHUNKING_VERSION,
    LEXICAL_CONFIG_SHA256,
    chunk_declared_corpus,
    load_declared_corpus_by_key,
)
from evalgate.adapters.fastembed_reference import FastEmbedReferenceEmbedding
from evalgate.adapters.postgres_ingestion import PostgresCorpusRepository
from evalgate.application.ingestion import ingest_declared_corpus
from evalgate.config import Settings
from evalgate.domain.corpus import IngestionError, IngestionErrorCode

API_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = API_ROOT.parents[1]
REFERENCE_MANIFEST = REPOSITORY_ROOT / "contracts" / "manifests" / "reference-embedding.json"


async def ingest(*, corpus_key: str, settings: Settings) -> dict[str, object]:
    """Run the sole declared-source ingestion path and return a safe report."""

    settings.provider_configuration()
    corpus = load_declared_corpus_by_key(corpus_key)
    if settings.environment == "public" or settings.embedding_mode.value != "reference":
        raise IngestionError(
            IngestionErrorCode.INGESTION_NOT_PERMITTED,
            "declared corpus ingestion requires non-public reference mode",
        )
    if settings.reference_embedding_snapshot is None:
        raise IngestionError(
            code=IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
            message="verified local reference embedding snapshot is unavailable",
        )
    embedding = FastEmbedReferenceEmbedding.from_verified_snapshot(
        manifest_path=REFERENCE_MANIFEST,
        snapshot_path=Path(settings.reference_embedding_snapshot),
    )
    chunked = chunk_declared_corpus(corpus, tokenizer=embedding)
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        report = await ingest_declared_corpus(
            corpus=chunked.corpus,
            chunks=chunked.chunks,
            embedding=embedding,
            repository=PostgresCorpusRepository(engine),
            chunking_version=CHUNKING_VERSION,
            chunking_policy_sha256=CHUNKING_POLICY_SHA256,
            lexical_config_sha256=LEXICAL_CONFIG_SHA256,
        )
    finally:
        engine.dispose()
    return {
        "status": report.status,
        "corpus_key": report.corpus_key,
        "corpus_version": report.corpus_version,
        "corpus_version_id": str(report.corpus_version_id),
        "index_version_id": str(report.index_version_id),
        "document_count": report.document_count,
        "chunk_count": report.chunk_count,
    }


def main() -> None:
    """Run local ingestion without exposing arbitrary filesystem or network input."""

    parser = argparse.ArgumentParser(prog="evalgate-ingest")
    parser.add_argument("--corpus", required=True, help="declared bundled corpus key")
    args = parser.parse_args()
    try:
        report = asyncio.run(ingest(corpus_key=args.corpus, settings=Settings()))
    except IngestionError as error:
        parser.error(f"{error.code}: {error}")
    print(json.dumps(report, sort_keys=True))
