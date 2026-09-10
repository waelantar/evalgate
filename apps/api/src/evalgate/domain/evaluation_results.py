"""Validated bounded projection of a reviewed evaluation artifact."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

MAX_ARTIFACT_BYTES = 1_000_000
MAX_CASES = 100


@dataclass(frozen=True, slots=True)
class EvaluationArtifact:
    artifact_sha256: str
    run_key: str
    mode: str
    status: str
    code_sha: str
    dataset_manifest_sha256: str
    corpus_manifest_sha256: str
    index_key: str
    policy_version: str
    versions: dict[str, Any]
    environment: dict[str, Any]
    metrics: dict[str, float]
    limitations: tuple[str, ...]
    cases: tuple[dict[str, Any], ...]


def parse_artifact(raw: bytes, schema: dict[str, Any]) -> EvaluationArtifact:
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("evaluation artifact exceeds the import size limit")
    import json

    value = json.loads(raw)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    cases = value["cases"]
    if len(cases) > MAX_CASES:
        raise ValueError("evaluation artifact exceeds the case limit")
    versions = value["versions"]
    run = value["run"]
    return EvaluationArtifact(
        artifact_sha256=sha256(raw).hexdigest(),
        run_key=run["run_key"],
        mode=run["mode"],
        status=run["status"],
        code_sha=versions["code_sha"],
        dataset_manifest_sha256=versions["dataset_manifest_sha256"],
        corpus_manifest_sha256=versions["corpus_manifest_sha256"],
        index_key=versions["index_key"],
        policy_version=versions["policy_version"],
        versions=dict(versions),
        environment=dict(value["environment"]),
        metrics=value["metrics"],
        limitations=tuple(value["limitations"]),
        cases=tuple(cases),
    )
