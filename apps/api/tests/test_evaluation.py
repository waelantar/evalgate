import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evalgate.domain.evaluation import (
    citation_coverage,
    citation_validity,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from evalgate.entrypoints.evaluate import build_artifact


def test_rank_metrics_and_zero_denominators() -> None:
    retrieved = ["b", "a", "c"]
    assert precision_at_k(retrieved, {"a", "c"}, 2) == 0.5
    assert recall_at_k(retrieved, {"a", "c"}, 2) == 0.5
    assert recall_at_k(retrieved, set(), 2) == 0.0
    assert reciprocal_rank(retrieved, {"a"}) == 0.5
    assert ndcg_at_k(retrieved, {"a": 2, "c": 1}, 3) > 0


def test_metrics_reject_invalid_k() -> None:
    with pytest.raises(ValueError):
        precision_at_k([], set(), 0)
    with pytest.raises(ValueError):
        ndcg_at_k([], {}, 0)


def test_citation_metrics_exclude_invalid_and_uncovered_claims() -> None:
    citations = [
        {"evidence_id": "e1", "claim": "supported"},
        {"evidence_id": "bad", "claim": "other"},
    ]
    assert citation_validity(citations, {"e1"}) == 0.5
    assert citation_coverage(citations, {"supported", "missing"}) == 0.5


def test_golden_dataset_has_reviewed_declared_splits() -> None:
    path = Path(__file__).parents[3] / "contracts/evaluation/golden-v1.json"
    dataset = json.loads(path.resolve().read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) == 36
    assert sum(case["split"] == "development" for case in cases) == 18
    assert sum(case["split"] == "calibration" for case in cases) == 6
    assert sum(case["split"] == "regression" for case in cases) == 12
    assert all(case["review_state"] == "reviewed" for case in cases)


def test_fixture_artifact_validates_against_contract() -> None:
    root = Path(__file__).parents[3]
    schema_path = root / "contracts/evaluation/artifact.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    artifact = build_artifact(root / "contracts/evaluation/golden-v1.json")
    Draft202012Validator(schema).validate(artifact)
