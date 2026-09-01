import json
from pathlib import Path

import pytest

from evalgate.domain.evaluation_results import MAX_ARTIFACT_BYTES, parse_artifact


def test_artifact_projection_validates_and_hashes() -> None:
    root = Path(__file__).parents[3]
    schema = json.loads((root / "contracts/evaluation/artifact.schema.json").read_text())
    raw = json.dumps(
        {
            "schema_version": "1.0",
            "run": {
                "run_key": "r",
                "mode": "retrieval",
                "status": "completed",
                "started_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:00:00Z",
            },
            "versions": {
                "code_sha": "0" * 40,
                "corpus_manifest_sha256": "0" * 64,
                "index_key": "i",
                "dataset_manifest_sha256": "1" * 64,
                "policy_version": "p",
            },
            "environment": {
                "os": "x",
                "architecture": "x",
                "python": "x",
                "postgres_image_digest": "x",
                "numeric_tolerance": 0,
            },
            "metrics": {"mrr": 1.0},
            "cases": [],
            "limitations": ["fixture"],
        }
    ).encode()
    artifact = parse_artifact(raw, schema)
    assert artifact.run_key == "r"
    assert len(artifact.artifact_sha256) == 64


def test_artifact_size_limit_fails_before_parsing() -> None:
    with pytest.raises(ValueError, match="size limit"):
        parse_artifact(b" " * (MAX_ARTIFACT_BYTES + 1), {})
