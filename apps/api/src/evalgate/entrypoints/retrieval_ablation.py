"""Independent stdin-only retrieval ablation diagnostic."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections.abc import Sequence
from time import perf_counter_ns
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine

from evalgate import __version__
from evalgate.application.search import MAX_QUERY_CODE_POINTS, SearchRequest, search_corpus
from evalgate.config import Settings
from evalgate.domain.search import HYBRID_RRF_V1, RetrievalMode, SearchResult
from evalgate.entrypoints.retrieval_runtime import build_reference_retrieval, database_event_loop

_MODES = tuple(RetrievalMode)


def _percentile(samples: Sequence[float], percentile: float) -> float:
    ordered = sorted(samples)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _timings(samples: Sequence[float]) -> dict[str, float | int]:
    return {
        "sample_count": len(samples),
        "min_ms": min(samples),
        "p50_ms": _percentile(samples, 0.50),
        "p95_ms": _percentile(samples, 0.95),
        "max_ms": max(samples),
    }


def _evidence(result: SearchResult) -> list[dict[str, object]]:
    return [
        {
            "evidence_id": str(item.evidence.evidence_id),
            "rank": item.rank,
            "lexical_rank": item.lexical_rank,
            "vector_rank": item.vector_rank,
            "rrf_score": item.rrf_score,
        }
        for item in result.evidence
    ]


async def run_ablation(
    *,
    query: str,
    index_version: UUID,
    modes: Sequence[RetrievalMode],
    warmups: int,
    repetitions: int,
    limit: int,
    settings: Settings,
) -> dict[str, Any]:
    """Run bounded real retrieval repetitions without retaining query or chunk content."""

    engine = create_async_engine(
        settings.database_url.get_secret_value(), pool_pre_ping=True, pool_recycle=300
    )
    try:
        repository, embedding = build_reference_retrieval(settings=settings, engine=engine)
        mode_reports: dict[str, object] = {}
        selected: SearchResult | None = None
        for mode in modes:
            request = SearchRequest(
                query=query, index_version=index_version, limit=limit, mode=mode
            )
            for _ in range(warmups):
                await search_corpus(request=request, embedding=embedding, repository=repository)
            samples: list[float] = []
            result: SearchResult | None = None
            for _ in range(repetitions):
                started = perf_counter_ns()
                result = await search_corpus(
                    request=request, embedding=embedding, repository=repository
                )
                samples.append((perf_counter_ns() - started) / 1_000_000)
            if result is None:  # bounded parser validation makes this unreachable
                raise RuntimeError("retrieval ablation produced no samples")
            if selected is not None and result.index != selected.index:
                raise RuntimeError("retrieval ablation index identity changed")
            selected = result
            mode_reports[mode.value] = {
                "evidence": _evidence(result),
                "timings": _timings(samples),
            }
        if selected is None:
            raise RuntimeError("retrieval ablation selected no modes")
        index = selected.index
        return {
            "product": {"name": "evalgate-api", "version": __version__},
            "retrieval_policy": {
                "id": HYBRID_RRF_V1.policy_id,
                "lexical_candidate_depth": HYBRID_RRF_V1.lexical_candidate_depth,
                "vector_candidate_depth": HYBRID_RRF_V1.vector_candidate_depth,
                "rrf_constant": HYBRID_RRF_V1.rrf_constant,
            },
            "index": {
                "version_id": str(index.index_version_id),
                "key": index.index_key,
                "chunking_version": index.chunking_version,
                "chunking_policy_sha256": index.chunking_policy_sha256,
                "lexical_config_sha256": index.lexical_config_sha256,
                "embedding": {
                    "model": index.embedding_model,
                    "revision": index.embedding_revision,
                    "checksum": index.embedding_checksum,
                    "dimension": index.embedding_dimension,
                },
            },
            "source_corpus": {
                "version_id": str(index.corpus_version_id),
                "key": index.corpus_key,
                "version": index.corpus_version,
                "manifest_sha256": index.corpus_manifest_sha256,
            },
            "configuration": {
                "warmups": warmups,
                "repetitions": repetitions,
                "limit": limit,
            },
            "modes": mode_reports,
            "limitations": [
                "Diagnostic timings are observations on this runtime and corpus, "
                "not a latency promise.",
                "This command does not compute quality metrics, thresholds, "
                "or a reviewed baseline.",
            ],
        }
    finally:
        await engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evalgate-retrieval-ablation")
    parser.add_argument("--index-version", required=True, type=UUID)
    parser.add_argument("--mode", action="append", choices=[mode.value for mode in _MODES])
    parser.add_argument("--warmups", type=int, default=1, choices=range(0, 11))
    parser.add_argument("--repetitions", type=int, default=5, choices=range(1, 101))
    parser.add_argument("--limit", type=int, default=10, choices=range(1, 21))
    return parser


def main() -> None:
    """Read one private query from stdin and emit only content-free JSON diagnostics."""

    parser = _parser()
    args = parser.parse_args()
    query = sys.stdin.read(MAX_QUERY_CODE_POINTS + 1)
    modes = tuple(RetrievalMode(value) for value in (args.mode or [mode.value for mode in _MODES]))
    try:
        report = asyncio.run(
            run_ablation(
                query=query,
                index_version=args.index_version,
                modes=modes,
                warmups=args.warmups,
                repetitions=args.repetitions,
                limit=args.limit,
                settings=Settings(),
            ),
            loop_factory=database_event_loop,
        )
    except Exception:
        parser.exit(1, "evalgate-retrieval-ablation: retrieval_ablation.failed\n")
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
