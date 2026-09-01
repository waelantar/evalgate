import json
import subprocess
import sys
from pathlib import Path


def test_baseline_accepts_reference_and_rejects_known_bad(tmp_path: Path) -> None:
    root = Path(__file__).parents[3]
    baseline = root / "contracts/evaluation/retrieval-baseline-v1.json"
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        json.dumps(
            {
                "run": {"mode": "retrieval", "status": "completed"},
                "versions": {"policy_version": "hybrid-rrf-v1"},
                "metrics": {
                    "retrieval_precision_at_5": 0.14,
                    "retrieval_recall_at_5": 0.72,
                    "mrr": 0.60,
                    "ndcg_at_5": 0.63,
                    "source_coverage": 0.72,
                },
            }
        ),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        str(root / "scripts/check_retrieval_baseline.py"),
        "--artifact",
        str(artifact),
        "--baseline",
        str(baseline),
    ]
    assert subprocess.run(command, check=False).returncode == 0
    artifact.write_text(
        artifact.read_text(encoding="utf-8").replace("0.72", "0.00", 1), encoding="utf-8"
    )
    assert subprocess.run(command, check=False).returncode != 0
