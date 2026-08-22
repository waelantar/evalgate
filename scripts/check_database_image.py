"""Verify the locally available PostgreSQL/pgvector image registry digest."""

from __future__ import annotations

import json
import subprocess
import sys

IMAGE = (
    "pgvector/pgvector:0.8.5-pg18-trixie@"
    "sha256:9d2e61c7352b9e9f4798df5fd9a498f043f4cda1cdacc707de3d198650f4321e"
)
REPOSITORY_DIGEST = (
    "pgvector/pgvector@"
    "sha256:9d2e61c7352b9e9f4798df5fd9a498f043f4cda1cdacc707de3d198650f4321e"
)


def main() -> int:
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE, "--format", "{{json .RepoDigests}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Database image check failed: reviewed image is not available.", file=sys.stderr)
        return 1

    try:
        repo_digests = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Database image check failed: Docker returned invalid metadata.", file=sys.stderr)
        return 1
    if REPOSITORY_DIGEST not in repo_digests:
        print("Database image check failed: registry digest does not match.", file=sys.stderr)
        return 1

    print("Database image check passed: reviewed PostgreSQL/pgvector digest is present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
