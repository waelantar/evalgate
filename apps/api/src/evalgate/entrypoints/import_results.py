"""Local-admin import of one reviewed, schema-valid evaluation artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine, text

from evalgate.config import Settings
from evalgate.domain.evaluation_results import parse_artifact


def import_artifact(*, artifact_path: Path, schema_path: Path, settings: Settings) -> str:
    raw = artifact_path.read_bytes()
    artifact = parse_artifact(raw, json.loads(schema_path.read_text(encoding="utf-8")))
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with engine.begin() as connection:
            index = connection.execute(
                text("SELECT id FROM index_versions WHERE index_key = :key"),
                {"key": artifact.index_key},
            ).scalar_one_or_none()
            if index is None:
                raise ValueError("artifact references an unknown index")
            existing = connection.execute(
                text("SELECT artifact_sha256 FROM eval_runs WHERE run_key = :key"),
                {"key": artifact.run_key},
            ).scalar_one_or_none()
            if existing == artifact.artifact_sha256:
                return "already_imported"
            if existing is not None:
                raise ValueError("run key already belongs to a different artifact")
            dataset_id = uuid5(
                NAMESPACE_URL, f"urn:evalgate:dataset:{artifact.dataset_manifest_sha256}"
            )
            connection.execute(
                text(
                    "INSERT INTO eval_datasets (id, version, manifest_sha256, review_status) "
                    "VALUES (:id, :version, :sha, 'reviewed') ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": dataset_id,
                    "version": artifact.dataset_manifest_sha256,
                    "sha": artifact.dataset_manifest_sha256,
                },
            )
            run_id = uuid5(NAMESPACE_URL, f"urn:evalgate:run:{artifact.artifact_sha256}")
            connection.execute(
                text(
                    "INSERT INTO eval_runs (id, run_key, index_version_id, eval_dataset_id, "
                    "mode, status, code_sha, version_manifest, artifact_sha256) VALUES "
                    "(:id, :key, :index, "
                    ":dataset, :mode, :status, :code, :versions::jsonb, :sha)"
                ),
                {
                    "id": run_id,
                    "key": artifact.run_key,
                    "index": index,
                    "dataset": dataset_id,
                    "mode": artifact.mode,
                    "status": artifact.status,
                    "code": artifact.code_sha,
                    "versions": json.dumps(
                        {
                            "index_key": artifact.index_key,
                            "metrics": artifact.metrics,
                            "limitations": artifact.limitations,
                        }
                    ),
                    "sha": artifact.artifact_sha256,
                },
            )
            return "imported"
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    print(
        import_artifact(
            artifact_path=args.artifact,
            schema_path=root / "contracts/evaluation/artifact.schema.json",
            settings=Settings(),
        )
    )


if __name__ == "__main__":
    main()
