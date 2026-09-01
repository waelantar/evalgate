"""Compare one retrieval artifact against the reviewed, immutable PR baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    if artifact["run"]["mode"] != "retrieval" or artifact["run"]["status"] != "completed":
        raise SystemExit("retrieval artifact is not a completed retrieval run")
    if artifact["versions"]["policy_version"] != baseline["policy_version"]:
        raise SystemExit("retrieval policy identity differs from reviewed baseline")
    failed = [
        f"{metric}: {artifact['metrics'].get(metric)} < {minimum}"
        for metric, minimum in baseline["required_metrics"].items()
        if artifact["metrics"].get(metric, -1) < minimum
    ]
    if failed:
        raise SystemExit("retrieval regression: " + "; ".join(failed))
    print("retrieval baseline: pass")


if __name__ == "__main__":
    main()
