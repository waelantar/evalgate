"""Trust-boundary and environment tests for evaluation result import."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from pydantic import SecretStr

from evalgate.application.provider_configuration import EmbeddingMode, GenerationMode
from evalgate.config import Settings
from evalgate.entrypoints.http import create_app
from evalgate.entrypoints.import_results import _load_reviewed_dataset, import_artifact


def test_unreviewed_dataset_and_wrong_dataset_checksum_are_rejected(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_version": "1.0.0",
                "cases": [
                    {
                        "case_id": "case-1",
                        "split": "development",
                        "question": "Question?",
                        "answerability": "answerable",
                        "relevant_evidence_ids": [],
                        "supported_claims": [],
                        "review_state": "draft",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    checksum = sha256(dataset_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="unreviewed"):
        _load_reviewed_dataset(dataset_path, checksum)
    with pytest.raises(ValueError, match="different evaluation dataset checksum"):
        _load_reviewed_dataset(dataset_path, "0" * 64)


def test_import_is_denied_outside_local_admin_before_reading_files(tmp_path: Path) -> None:
    for environment in ("ci", "trusted_evaluation", "public"):
        with pytest.raises(ValueError, match="only in local"):
            import_artifact(
                artifact_path=tmp_path / "missing-artifact",
                schema_path=tmp_path / "missing-schema",
                dataset_path=tmp_path / "missing-dataset",
                review_path=tmp_path / "missing-review",
                review_schema_path=tmp_path / "missing-review-schema",
                settings=Settings(
                    environment=environment,
                    database_url=SecretStr("postgresql+psycopg://ignored/ignored"),
                    allowed_origins="https://demo.example",
                    rate_identity_secret=SecretStr("s" * 32),
                ),
            )


def test_public_application_exposes_only_get_result_routes() -> None:
    app = create_app(
        settings=Settings(
            environment="public",
            database_url=SecretStr("postgresql+psycopg://ignored/ignored"),
            embedding_mode=EmbeddingMode.REFERENCE,
            generation_mode=GenerationMode.DISABLED,
            reference_embedding_snapshot="ignored",
            allowed_origins="https://demo.example",
            rate_identity_secret=SecretStr("s" * 32),
            generation_maximum_input_tokens=2048,
            generation_maximum_output_tokens=1024,
            generation_per_client_concurrency=1,
            generation_global_concurrency=2,
            generation_daily_request_allowance=10,
            generation_provider_account_cap_usd=1.0,
        ),
        engine=object(),  # type: ignore[arg-type]
        search_repository=object(),  # type: ignore[arg-type]
        search_embedding=object(),  # type: ignore[arg-type]
    )
    result_routes = {
        route.path: route.methods
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/evaluation-runs")
    }
    assert result_routes
    assert all(methods == {"GET"} for methods in result_routes.values())


def test_ci_workflow_has_no_result_import_command() -> None:
    workflow = (Path(__file__).parents[3] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "evalgate-import-results" not in workflow


def test_live_evaluation_workflow_is_manual_only_and_uses_secret() -> None:
    workflow = (Path(__file__).parents[3] / ".github/workflows/live-evaluation.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "pull_request" not in workflow
    assert "pull_request_target" not in workflow
    assert "EVALGATE_OPENROUTER_API_KEY: ${{ secrets.EVALGATE_OPENROUTER_API_KEY }}" in workflow
    assert "evalgate-live-evaluate" in workflow


def test_tampered_artifact_fails_approved_checksum_before_database(tmp_path: Path) -> None:
    root = Path(__file__).parents[3]
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "run": {
                    "run_key": "tampered",
                    "mode": "retrieval",
                    "status": "completed",
                    "started_at": "2026-09-02T00:00:00Z",
                    "finished_at": "2026-09-02T00:00:01Z",
                },
                "versions": {
                    "code_sha": "a" * 40,
                    "corpus_manifest_sha256": "b" * 64,
                    "index_key": "index",
                    "dataset_manifest_sha256": "c" * 64,
                    "policy_version": "hybrid-rrf-v1",
                },
                "environment": {
                    "os": "test",
                    "architecture": "test",
                    "python": "3.13.15",
                    "postgres_image_digest": "sha256:test",
                    "numeric_tolerance": 0,
                },
                "metrics": {},
                "cases": [],
                "limitations": ["test"],
            }
        ),
        encoding="utf-8",
    )
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "artifact_sha256": "d" * 64,
                "dataset_manifest_sha256": "c" * 64,
                "decision": "approved",
                "reviewer_role": "test-maintainer",
                "reviewed_at": "2026-09-02T00:00:02Z",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="artifact checksum"):
        import_artifact(
            artifact_path=artifact_path,
            schema_path=root / "contracts/evaluation/artifact.schema.json",
            dataset_path=root / "contracts/evaluation/golden-v1.json",
            review_path=review_path,
            review_schema_path=root / "contracts/evaluation/review-record.schema.json",
            settings=Settings(),
        )
