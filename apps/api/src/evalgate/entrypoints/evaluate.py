"""Produce a deterministic, schema-shaped fixture evaluation artifact."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine

from evalgate import __version__
from evalgate.application.search import SearchRequest, search_corpus
from evalgate.config import Settings
from evalgate.domain.evaluation import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from evalgate.domain.search import RetrievalMode
from evalgate.entrypoints.retrieval_runtime import build_reference_retrieval, database_event_loop


def build_artifact(dataset_path: Path) -> dict[str, Any]:
    raw = dataset_path.read_bytes()
    dataset = json.loads(raw)
    now = datetime.now(UTC).isoformat()
    return {
        "schema_version": "1.0",
        "run": {
            "run_key": "fixture-contract",
            "mode": "fixture_contract",
            "status": "completed",
            "started_at": now,
            "finished_at": now,
        },
        "versions": {
            "code_sha": "0" * 40,
            "corpus_manifest_sha256": "0" * 64,
            "index_key": "fixture-v1",
            "dataset_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "policy_version": "hybrid-rrf-v1",
        },
        "environment": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "postgres_image_digest": "not-run",
            "numeric_tolerance": 1e-9,
        },
        "metrics": {
            "case_count": float(len(dataset["cases"])),
            "retrieval_precision_at_5": 0.0,
            "retrieval_recall_at_5": 0.0,
            "citation_validity": 0.0,
            "citation_coverage": 0.0,
        },
        "cases": dataset["cases"],
        "limitations": [
            "Fixture contract mode does not call a provider, judge, PostgreSQL, or embedding "
            "runtime.",
            "code_sha and corpus identity are placeholders until a governed retrieval run "
            "supplies them.",
        ],
    }


def render_markdown(artifact: dict[str, Any]) -> str:
    run = artifact["run"]
    versions = artifact["versions"]
    metrics = artifact["metrics"]
    limitations = artifact["limitations"]
    lines = [
        "# EvalGate evaluation artifact",
        "",
        f"- Run: `{run['run_key']}` ({run['mode']})",
        f"- Status: `{run['status']}`",
        f"- Dataset manifest: `{versions['dataset_manifest_sha256']}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in metrics.items())
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in limitations)
    return "\n".join(lines) + "\n"


async def build_retrieval_artifact(
    dataset_path: Path, index_version: str, settings: Settings
) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    try:
        repository, embedding = build_reference_retrieval(settings=settings, engine=engine)
        results: list[dict[str, Any]] = []
        precisions: list[float] = []
        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcgs: list[float] = []
        source_hits = 0
        index_uuid = __import__("uuid").UUID(index_version)
        selected_index: Any = None
        for case in dataset["cases"]:
            result = await search_corpus(
                request=SearchRequest(
                    query=case["question"],
                    index_version=index_uuid,
                    limit=5,
                    mode=RetrievalMode.HYBRID,
                ),
                embedding=embedding,
                repository=repository,
            )
            selected_index = result.index
            retrieved = [str(item.evidence.evidence_id) for item in result.evidence]
            relevant = set(case["relevant_evidence_ids"])
            precisions.append(precision_at_k(retrieved, relevant, 5))
            recalls.append(recall_at_k(retrieved, relevant, 5))
            reciprocal_ranks.append(reciprocal_rank(retrieved, relevant))
            ndcgs.append(ndcg_at_k(retrieved, {item: 1 for item in relevant}, 5))
            source_hits += bool(set(retrieved) & relevant)
            results.append(
                {
                    "case_id": case["case_id"],
                    "retrieved_evidence_ids": retrieved,
                    "relevant_evidence_ids": list(relevant),
                }
            )
        if selected_index is None:
            raise RuntimeError("evaluation dataset is empty")
        raw = dataset_path.read_bytes()
        code_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        return {
            "schema_version": "1.0",
            "run": {
                "run_key": "golden-v1-hybrid",
                "mode": "retrieval",
                "status": "completed",
                "started_at": "2026-08-31T00:00:00Z",
                "finished_at": "2026-08-31T00:00:00Z",
            },
            "versions": {
                "code_sha": code_sha,
                "corpus_manifest_sha256": selected_index.corpus_manifest_sha256,
                "index_key": selected_index.index_key,
                "dataset_manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "policy_version": "hybrid-rrf-v1",
            },
            "environment": {
                "os": platform.system(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "postgres_image_digest": (
                    "sha256:9d2e61c7352b9e9f4798df5fd9a498f043f4cda1cdacc707de3d198650f4321e"
                ),
                "numeric_tolerance": 1e-9,
            },
            "metrics": {
                "case_count": float(len(results)),
                "retrieval_precision_at_5": sum(precisions) / len(precisions),
                "retrieval_recall_at_5": sum(recalls) / len(recalls),
                "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
                "ndcg_at_5": sum(ndcgs) / len(ndcgs),
                "source_coverage": source_hits / max(1, len(results)),
                "citation_validity": 0.0,
                "citation_coverage": 0.0,
            },
            "cases": results,
            "limitations": [
                "Retrieval mode evaluates ranking evidence only; generation and judge scoring "
                "are not performed.",
                "Timing observations are collected separately by evalgate-retrieval-ablation "
                "and are not release thresholds.",
            ],
        }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    repository_root = Path(__file__).resolve().parents[5]
    parser.add_argument(
        "--dataset", type=Path, default=repository_root / "contracts/evaluation/golden-v1.json"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation-fixture.json"))
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--mode", choices=["fixture", "retrieval"], default="fixture")
    parser.add_argument("--index-version", default=None)
    args = parser.parse_args()
    if args.mode == "retrieval":
        if args.index_version is None:
            parser.error("--index-version is required for retrieval mode")
        artifact = asyncio.run(
            build_retrieval_artifact(args.dataset, args.index_version, Settings()),
            loop_factory=database_event_loop,
        )
    else:
        artifact = build_artifact(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(artifact), encoding="utf-8")
    print(f"wrote {args.output} for EvalGate {__version__}")


if __name__ == "__main__":
    main()
