"""Local import of one reviewed, immutable evaluation artifact projection."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from sqlalchemy import create_engine, text

from evalgate.application.runtime_security import environment_policy
from evalgate.config import Settings
from evalgate.domain.evaluation_results import EvaluationArtifact, parse_artifact


@dataclass(frozen=True, slots=True)
class ReviewedDataset:
    version: str
    manifest_sha256: str
    cases: dict[str, dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _load_reviewed_dataset(path: Path, expected_sha256: str) -> ReviewedDataset:
    raw = path.read_bytes()
    manifest_sha256 = sha256(raw).hexdigest()
    if manifest_sha256 != expected_sha256:
        raise ValueError("artifact references a different evaluation dataset checksum")
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError("evaluation dataset has an unsupported schema")
    version = value.get("dataset_version")
    raw_cases = value.get("cases")
    if not isinstance(version, str) or not version or not isinstance(raw_cases, list):
        raise ValueError("evaluation dataset identity is invalid")
    cases: dict[str, dict[str, Any]] = {}
    for case in raw_cases:
        if not isinstance(case, dict):
            raise ValueError("evaluation dataset contains an invalid case")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in cases:
            raise ValueError("evaluation dataset case identities are invalid")
        if case.get("review_state") != "reviewed":
            raise ValueError("evaluation dataset contains an unreviewed case")
        if not isinstance(case.get("question"), str) or not case["question"]:
            raise ValueError("evaluation dataset contains an invalid question")
        if case.get("answerability") not in {"answerable", "unanswerable"}:
            raise ValueError("evaluation dataset contains invalid answerability")
        if not isinstance(case.get("split"), str) or not case["split"]:
            raise ValueError("evaluation dataset contains an invalid split")
        if not isinstance(case.get("relevant_evidence_ids"), list) or not isinstance(
            case.get("supported_claims"), list
        ):
            raise ValueError("evaluation dataset contains invalid reviewed evidence")
        cases[case_id] = case
    return ReviewedDataset(version=version, manifest_sha256=manifest_sha256, cases=cases)


def _validate_review(
    *, artifact: EvaluationArtifact, review_path: Path, review_schema_path: Path
) -> dict[str, Any]:
    review = _load_json(review_path)
    Draft202012Validator(_load_json(review_schema_path), format_checker=FormatChecker()).validate(
        review
    )
    if review["artifact_sha256"] != artifact.artifact_sha256:
        raise ValueError("artifact checksum does not match its approved review record")
    if review["dataset_manifest_sha256"] != artifact.dataset_manifest_sha256:
        raise ValueError("dataset checksum does not match the approved review record")
    return review


def _validated_cases(
    artifact: EvaluationArtifact, dataset: ReviewedDataset
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    artifact_cases: dict[str, dict[str, Any]] = {}
    for case in artifact.cases:
        case_id = case["case_id"]
        if case_id in artifact_cases:
            raise ValueError("artifact contains duplicate case identities")
        artifact_cases[case_id] = case
    if set(artifact_cases) != set(dataset.cases):
        raise ValueError("artifact cases do not exactly match the reviewed dataset")
    validated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case_id, artifact_case in artifact_cases.items():
        dataset_case = dataset.cases[case_id]
        if artifact_case["relevant_evidence_ids"] != dataset_case["relevant_evidence_ids"]:
            raise ValueError("artifact relevant evidence differs from the reviewed dataset")
        validated.append((artifact_case, dataset_case))
    return validated


def import_artifact(
    *,
    artifact_path: Path,
    schema_path: Path,
    dataset_path: Path,
    review_path: Path,
    review_schema_path: Path,
    settings: Settings,
) -> str:
    """Validate trust inputs before atomically persisting their bounded projection."""

    if not environment_policy(settings.environment).allow_result_import:
        raise ValueError("evaluation artifact import is available only in local admin mode")
    artifact = parse_artifact(artifact_path.read_bytes(), _load_json(schema_path))
    review = _validate_review(
        artifact=artifact, review_path=review_path, review_schema_path=review_schema_path
    )
    if artifact.mode != "retrieval":
        raise ValueError("only reviewed retrieval artifacts can be imported")
    dataset = _load_reviewed_dataset(dataset_path, artifact.dataset_manifest_sha256)
    cases = _validated_cases(artifact, dataset)
    if artifact.policy_version != "hybrid-rrf-v1":
        raise ValueError("retrieval artifact references an unsupported policy")

    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with engine.begin() as connection:
            index = (
                connection.execute(
                    text(
                        "SELECT iv.id, cv.manifest_sha256 FROM index_versions iv "
                        "JOIN corpus_versions cv ON cv.id = iv.corpus_version_id "
                        "WHERE iv.index_key = :key"
                    ),
                    {"key": artifact.index_key},
                )
                .mappings()
                .one_or_none()
            )
            if index is None:
                raise ValueError("artifact references an unknown index")
            if index["manifest_sha256"] != artifact.corpus_manifest_sha256:
                raise ValueError("artifact corpus checksum does not match the referenced index")

            existing = connection.execute(
                text("SELECT artifact_sha256 FROM eval_runs WHERE run_key = :key"),
                {"key": artifact.run_key},
            ).scalar_one_or_none()
            if existing == artifact.artifact_sha256:
                return "already_imported"
            if existing is not None:
                raise ValueError("run key already belongs to a different artifact")

            dataset_id = uuid5(NAMESPACE_URL, f"urn:evalgate:dataset:{dataset.manifest_sha256}")
            stored_dataset = (
                connection.execute(
                    text(
                        "SELECT manifest_sha256, review_status FROM eval_datasets "
                        "WHERE version = :version"
                    ),
                    {"version": dataset.version},
                )
                .mappings()
                .one_or_none()
            )
            if stored_dataset is not None and (
                stored_dataset["manifest_sha256"] != dataset.manifest_sha256
                or stored_dataset["review_status"] != "reviewed"
            ):
                raise ValueError("stored evaluation dataset conflicts with the reviewed manifest")
            connection.execute(
                text(
                    "INSERT INTO eval_datasets (id, version, manifest_sha256, review_status) "
                    "VALUES (:id, :version, :sha, 'reviewed') ON CONFLICT (version) DO NOTHING"
                ),
                {"id": dataset_id, "version": dataset.version, "sha": dataset.manifest_sha256},
            )

            for _, dataset_case in cases:
                case_key = dataset_case["case_id"]
                case_id = uuid5(NAMESPACE_URL, f"urn:evalgate:case:{dataset_id}:{case_key}")
                connection.execute(
                    text(
                        "INSERT INTO eval_cases (id, dataset_id, stable_key, split, question, "
                        "answerable, reference_evidence, tags) VALUES (:id, :dataset, :key, "
                        ":split, :question, :answerable, CAST(:reference AS jsonb), "
                        "CAST(:tags AS jsonb)) ON CONFLICT (dataset_id, stable_key) DO NOTHING"
                    ),
                    {
                        "id": case_id,
                        "dataset": dataset_id,
                        "key": case_key,
                        "split": dataset_case["split"],
                        "question": dataset_case["question"],
                        "answerable": dataset_case["answerability"] == "answerable",
                        "reference": json.dumps(dataset_case["relevant_evidence_ids"]),
                        "tags": json.dumps(dataset_case["supported_claims"]),
                    },
                )

            run_id = uuid5(NAMESPACE_URL, f"urn:evalgate:run:{artifact.artifact_sha256}")
            version_manifest = {
                "versions": artifact.versions,
                "environment": artifact.environment,
                "metrics": artifact.metrics,
                "limitations": list(artifact.limitations),
                "review": {
                    "decision": review["decision"],
                    "reviewer_role": review["reviewer_role"],
                    "reviewed_at": review["reviewed_at"],
                },
            }
            connection.execute(
                text(
                    "INSERT INTO eval_runs (id, run_key, index_version_id, eval_dataset_id, "
                    "mode, status, code_sha, version_manifest, artifact_sha256) VALUES "
                    "(:id, :key, :index, :dataset, :mode, :status, :code, "
                    "CAST(:manifest AS jsonb), :sha)"
                ),
                {
                    "id": run_id,
                    "key": artifact.run_key,
                    "index": index["id"],
                    "dataset": dataset_id,
                    "mode": artifact.mode,
                    "status": artifact.status,
                    "code": artifact.code_sha,
                    "manifest": json.dumps(version_manifest),
                    "sha": artifact.artifact_sha256,
                },
            )

            for artifact_case, dataset_case in cases:
                case_key = dataset_case["case_id"]
                case_id = uuid5(NAMESPACE_URL, f"urn:evalgate:case:{dataset_id}:{case_key}")
                retrieved = artifact_case["retrieved_evidence_ids"]
                relevant = set(dataset_case["relevant_evidence_ids"])
                passed = (
                    bool(relevant.intersection(retrieved))
                    if dataset_case["answerability"] == "answerable"
                    else not retrieved
                )
                connection.execute(
                    text(
                        "INSERT INTO eval_case_results (id, eval_dataset_id, eval_run_id, "
                        "eval_case_id, retrieval_evidence, citation_evidence, metric_values, "
                        "status) VALUES (:id, :dataset, :run, :case, CAST(:retrieval AS jsonb), "
                        "'[]'::jsonb, CAST(:metrics AS jsonb), :status)"
                    ),
                    {
                        "id": uuid5(NAMESPACE_URL, f"urn:evalgate:result:{run_id}:{case_id}"),
                        "dataset": dataset_id,
                        "run": run_id,
                        "case": case_id,
                        "retrieval": json.dumps(retrieved),
                        "metrics": json.dumps({"retrieval_hit": 1.0 if passed else 0.0}),
                        "status": "passed" if passed else "failed",
                    },
                )
            return "imported"
    finally:
        engine.dispose()


def main() -> None:
    root = Path(__file__).resolve().parents[5]
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument(
        "--dataset", type=Path, default=root / "contracts/evaluation/golden-v1.json"
    )
    parser.add_argument("--review-record", required=True, type=Path)
    args = parser.parse_args()
    print(
        import_artifact(
            artifact_path=args.artifact,
            schema_path=root / "contracts/evaluation/artifact.schema.json",
            dataset_path=args.dataset,
            review_path=args.review_record,
            review_schema_path=root / "contracts/evaluation/review-record.schema.json",
            settings=Settings(),
        )
    )


if __name__ == "__main__":
    main()
