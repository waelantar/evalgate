"""Produce a deterministic, schema-shaped fixture evaluation artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

from evalgate import __version__


def build_artifact(dataset_path: Path) -> dict[str, object]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    repository_root = Path(__file__).resolve().parents[5]
    parser.add_argument(
        "--dataset", type=Path, default=repository_root / "contracts/evaluation/golden-v1.json"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation-fixture.json"))
    args = parser.parse_args()
    artifact = build_artifact(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} for EvalGate {__version__}")


if __name__ == "__main__":
    main()
