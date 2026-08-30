"""Fail-closed composition for real local retrieval dependencies."""

import asyncio
import selectors
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from evalgate.adapters.fastembed_reference import FastEmbedReferenceEmbedding
from evalgate.adapters.postgres_search import PostgresSearchRepository
from evalgate.application.provider_configuration import EmbeddingMode
from evalgate.config import Settings

API_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = API_ROOT.parents[1]
REFERENCE_MANIFEST = REPOSITORY_ROOT / "contracts" / "manifests" / "reference-embedding.json"


def database_event_loop() -> asyncio.AbstractEventLoop:
    """Create an event loop compatible with psycopg async connections on every platform."""

    if sys.platform == "win32":
        return asyncio.SelectorEventLoop(selectors.SelectSelector())
    return asyncio.new_event_loop()


def build_reference_retrieval(
    *, settings: Settings, engine: AsyncEngine
) -> tuple[PostgresSearchRepository, FastEmbedReferenceEmbedding]:
    """Construct real retrieval only for explicit, verified reference mode."""

    configuration = settings.provider_configuration()
    if configuration.embedding_mode is not EmbeddingMode.REFERENCE:
        raise ValueError("reference retrieval mode is not configured")
    if configuration.reference_snapshot_path is None:
        raise ValueError("reference retrieval snapshot is not configured")
    embedding = FastEmbedReferenceEmbedding.from_verified_snapshot(
        manifest_path=REFERENCE_MANIFEST,
        snapshot_path=Path(configuration.reference_snapshot_path),
    )
    return PostgresSearchRepository(engine), embedding
