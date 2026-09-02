"""Real PostgreSQL acceptance coverage for reviewed evaluation result imports."""

from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from evalgate.config import Settings
from evalgate.entrypoints.http import create_app
from evalgate.entrypoints.import_results import import_artifact
from evalgate.entrypoints.retrieval_runtime import database_event_loop

API_ROOT = Path(__file__).parents[2]
REPOSITORY_ROOT = API_ROOT.parents[1]
pytestmark = pytest.mark.integration


def _upgrade(database_url: str) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def _settings(
    database_url: str, environment: Literal["local", "ci", "public"] = "local"
) -> Settings:
    return Settings(environment=environment, database_url=SecretStr(database_url))


def _seed_index(database_url: str, *, corpus_sha256: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        corpus_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO corpus_versions "
                "(id, corpus_key, version, manifest_sha256, created_at) "
                "VALUES (:id, 'northstar-operations', '1.0.0', :sha, now())"
            ),
            {"id": corpus_id, "sha": corpus_sha256},
        )
        connection.execute(
            text(
                "INSERT INTO index_versions "
                "(id, corpus_version_id, index_key, chunking_version, "
                "chunking_policy_sha256, lexical_config_sha256, embedding_model, "
                "embedding_revision, embedding_checksum, embedding_dimension, created_at) "
                "VALUES (:id, :corpus, 'reviewed-index', 'chunk-v1', :sha, :sha, "
                "'model', 'revision', :sha, 384, now())"
            ),
            {"id": uuid4(), "corpus": corpus_id, "sha": "a" * 64},
        )
    engine.dispose()


def _write_inputs(tmp_path: Path, *, run_key: str = "reviewed-run") -> dict[str, Path]:
    dataset_path = REPOSITORY_ROOT / "contracts/evaluation/golden-v1.json"
    dataset_raw = dataset_path.read_bytes()
    dataset = json.loads(dataset_raw)
    artifact = {
        "schema_version": "1.0",
        "run": {
            "run_key": run_key,
            "mode": "retrieval",
            "status": "completed",
            "started_at": "2026-09-02T00:00:00Z",
            "finished_at": "2026-09-02T00:00:01Z",
        },
        "versions": {
            "code_sha": "b" * 40,
            "corpus_manifest_sha256": "c" * 64,
            "index_key": "reviewed-index",
            "dataset_manifest_sha256": sha256(dataset_raw).hexdigest(),
            "policy_version": "hybrid-rrf-v1",
        },
        "environment": {
            "os": "test",
            "architecture": "test",
            "python": "3.13.15",
            "postgres_image_digest": "sha256:test",
            "numeric_tolerance": 1e-9,
        },
        "metrics": {"case_count": 36.0, "mrr": 0.75},
        "cases": [
            {
                "case_id": case["case_id"],
                "retrieved_evidence_ids": case["relevant_evidence_ids"],
                "relevant_evidence_ids": case["relevant_evidence_ids"],
            }
            for case in dataset["cases"]
        ],
        "limitations": ["Reviewed fixture artifact."],
    }
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    review = {
        "schema_version": "1.0",
        "artifact_sha256": sha256(artifact_path.read_bytes()).hexdigest(),
        "dataset_manifest_sha256": sha256(dataset_raw).hexdigest(),
        "decision": "approved",
        "reviewer_role": "test-maintainer",
        "reviewed_at": "2026-09-02T00:00:02Z",
    }
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    return {
        "artifact_path": artifact_path,
        "schema_path": REPOSITORY_ROOT / "contracts/evaluation/artifact.schema.json",
        "dataset_path": dataset_path,
        "review_path": review_path,
        "review_schema_path": REPOSITORY_ROOT / "contracts/evaluation/review-record.schema.json",
    }


def test_reviewed_import_is_idempotent_and_persists_bounded_projection(
    database_url: str, tmp_path: Path
) -> None:
    _upgrade(database_url)
    _seed_index(database_url, corpus_sha256="c" * 64)
    inputs = _write_inputs(tmp_path)

    assert import_artifact(**inputs, settings=_settings(database_url)) == "imported"
    assert import_artifact(**inputs, settings=_settings(database_url)) == "already_imported"

    engine = create_engine(database_url)
    with engine.connect() as connection:
        counts = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM eval_datasets), "
                "(SELECT count(*) FROM eval_cases), (SELECT count(*) FROM eval_runs), "
                "(SELECT count(*) FROM eval_case_results)"
            )
        ).one()
        case = connection.execute(
            text("SELECT question, split FROM eval_cases WHERE stable_key = 'dev-01'")
        ).one()
        manifest = connection.execute(
            text("SELECT version_manifest FROM eval_runs WHERE run_key = 'reviewed-run'")
        ).scalar_one()
    engine.dispose()
    assert counts == (1, 36, 1, 36)
    assert case == ("What is the purpose of the Ledger Recovery Runbook?", "development")
    assert manifest["metrics"]["mrr"] == 0.75
    assert manifest["limitations"] == ["Reviewed fixture artifact."]
    assert "cases" not in manifest


def test_import_rolls_back_run_and_results_on_case_identity_conflict(
    database_url: str, tmp_path: Path
) -> None:
    _upgrade(database_url)
    _seed_index(database_url, corpus_sha256="c" * 64)
    inputs = _write_inputs(tmp_path, run_key="rollback-run")
    dataset_raw = inputs["dataset_path"].read_bytes()
    dataset_sha = sha256(dataset_raw).hexdigest()
    dataset_id = uuid5(NAMESPACE_URL, f"urn:evalgate:dataset:{dataset_sha}")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO eval_datasets (id, version, manifest_sha256, review_status) "
                "VALUES (:id, '1.0.0', :sha, 'reviewed')"
            ),
            {"id": dataset_id, "sha": dataset_sha},
        )
        connection.execute(
            text(
                "INSERT INTO eval_cases (id, dataset_id, stable_key, split, question, "
                "answerable, reference_evidence, tags) VALUES "
                "(:id, :dataset, 'dev-01', 'development', 'conflict', true, '[]', '[]')"
            ),
            {"id": uuid4(), "dataset": dataset_id},
        )
    with pytest.raises(IntegrityError):
        import_artifact(**inputs, settings=_settings(database_url))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM eval_runs")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM eval_case_results")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM eval_cases")).scalar_one() == 1
    engine.dispose()


@pytest.mark.parametrize(
    ("version_field", "value", "message"),
    [
        ("index_key", "missing-index", "unknown index"),
        ("corpus_manifest_sha256", "d" * 64, "corpus checksum"),
    ],
)
def test_import_rejects_unknown_or_mismatched_references_without_writes(
    database_url: str,
    tmp_path: Path,
    version_field: str,
    value: str,
    message: str,
) -> None:
    _upgrade(database_url)
    _seed_index(database_url, corpus_sha256="c" * 64)
    inputs = _write_inputs(tmp_path)
    artifact = json.loads(inputs["artifact_path"].read_text())
    artifact["versions"][version_field] = value
    inputs["artifact_path"].write_text(json.dumps(artifact), encoding="utf-8")
    review = json.loads(inputs["review_path"].read_text())
    review["artifact_sha256"] = sha256(inputs["artifact_path"].read_bytes()).hexdigest()
    inputs["review_path"].write_text(json.dumps(review), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        import_artifact(**inputs, settings=_settings(database_url))
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM eval_datasets")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM eval_runs")).scalar_one() == 0
    engine.dispose()


def test_results_api_paginates_details_deltas_and_failed_cases(
    database_url: str, tmp_path: Path
) -> None:
    _upgrade(database_url)
    _seed_index(database_url, corpus_sha256="c" * 64)
    first_dir = tmp_path / "first"
    first_dir.mkdir()
    first = _write_inputs(first_dir, run_key="baseline-run")
    second_dir = tmp_path / "second"
    second_dir.mkdir()
    second = _write_inputs(second_dir, run_key="candidate-run")
    candidate = json.loads(second["artifact_path"].read_text())
    candidate["metrics"]["mrr"] = 0.8
    candidate["cases"][0]["retrieved_evidence_ids"] = []
    second["artifact_path"].write_text(json.dumps(candidate), encoding="utf-8")
    review = json.loads(second["review_path"].read_text())
    review["artifact_sha256"] = sha256(second["artifact_path"].read_bytes()).hexdigest()
    second["review_path"].write_text(json.dumps(review), encoding="utf-8")
    import_artifact(**first, settings=_settings(database_url))
    import_artifact(**second, settings=_settings(database_url))

    async def exercise() -> None:
        engine = create_async_engine(database_url)
        app = create_app(settings=_settings(database_url), engine=engine)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            runs = await client.get("/api/v1/evaluation-runs", params={"limit": 1})
            assert runs.status_code == 200
            assert len(runs.json()["items"]) == 1
            assert runs.json()["next_cursor"] is not None
            detail = await client.get(
                "/api/v1/evaluation-runs/candidate-run", params={"compare_to": "baseline-run"}
            )
            assert detail.status_code == 200
            assert detail.json()["metric_deltas"]["mrr"] == pytest.approx(0.05)
            assert detail.json()["limitations"] == ["Reviewed fixture artifact."]
            cases = await client.get(
                "/api/v1/evaluation-runs/candidate-run/cases",
                params={"status": "failed", "limit": 10},
            )
            assert cases.status_code == 200
            assert [item["case_id"] for item in cases.json()["items"]] == ["dev-01"]
            assert (await client.get("/api/v1/evaluation-runs/missing")).status_code == 404
        await engine.dispose()

    asyncio.run(exercise(), loop_factory=database_event_loop)
