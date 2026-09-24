"""Validate release-candidate definitions without Docker or network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED_IMAGE = re.compile(r"^ARG PYTHON_BASE_IMAGE=python:3\.13\.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0$", re.MULTILINE)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    dockerfile = _read("Dockerfile")
    compose = _read("compose.yaml")
    release_script = _read("scripts/release_candidate.ps1")
    supply_script = _read("scripts/release_supply_chain.ps1")
    runbooks = _read("docs/runbooks/R3-operational-drills.md")
    evidence = _read("docs/release/EG-013D-release-candidate.md")

    if not PINNED_IMAGE.search(dockerfile):
        failures.append("Dockerfile: Python base image must be pinned by sha256 digest")
    for required in (
        "USER 10001:10001",
        "HEALTHCHECK",
        "/health/live",
        'LABEL org.opencontainers.image.version="0.12.3"',
        'CMD ["evalgate-api"]',
        "/usr/local/bin/python -m pip uninstall --yes pip",
    ):
        if required not in dockerfile:
            failures.append(f"Dockerfile: missing {required}")
    if "profiles: [\"release\"]" not in compose or "image: evalgate-api:0.12.3" not in compose:
        failures.append("compose.yaml: 0.12.3 release profile image definition is missing")
    if "condition: service_healthy" not in compose:
        failures.append("compose.yaml: API must wait for healthy PostgreSQL")
    for forbidden in ("docker push", "kubectl", "terraform", "opentofu"):
        if forbidden in (release_script + supply_script).lower():
            failures.append(f"release scripts: forbidden external operation appears: {forbidden}")
    for required in ("health/live", "health/ready", "10001:10001", "stop -t"):
        if required not in release_script:
            failures.append(f"scripts/release_candidate.ps1: missing {required}")
    if 'BUILDX_NO_DEFAULT_ATTESTATIONS = "1"' not in release_script:
        failures.append(
            "scripts/release_candidate.ps1: runtime scan build must disable default attestations"
        )
    for required in (
        "cyclonedx",
        "aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969",
        '"--severity", "high,critical"',
        '"--ignore-unfixed"',
        '"--exit-code", "1"',
        "eg-022-scan-actionable.json",
        "eg-022-scan-all.json",
        "eg-022-sbom.cdx.json",
    ):
        if required not in supply_script.lower():
            failures.append(f"scripts/release_supply_chain.ps1: missing {required}")
    for required in (
        "Graceful shutdown",
        "Provider outage and cooldown",
        "Database reset and restore",
        "Previous-image rollback",
        "Credential exposure and rotation",
        "Public generation kill switch",
        "Last drill result",
    ):
        if required not in runbooks:
            failures.append(f"docs/runbooks/R3-operational-drills.md: missing {required}")
    for required in (
        "evalgate-api:0.9.0",
        "artifacts/release/eg-013d-smoke.json",
        "artifacts/release/eg-013d-sbom.cdx.json",
        "not pushed, not deployed, and not released",
    ):
        if required not in evidence:
            failures.append(f"docs/release/EG-013D-release-candidate.md: missing {required}")
    try:
        json.loads(_read("contracts/release/eg-013d-evidence.schema.json"))
    except json.JSONDecodeError as error:
        failures.append(f"contracts/release/eg-013d-evidence.schema.json: invalid JSON: {error}")

    if failures:
        print("Release static check failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Release static check passed: image, Compose, scripts, runbooks, and evidence docs are bounded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
