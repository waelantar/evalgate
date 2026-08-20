"""Reference embedding manifest and snapshot-verification tests."""

from __future__ import annotations

import json
from hashlib import sha1, sha256
from pathlib import Path

import pytest

from evalgate.adapters.reference_embedding import (
    ReferenceSnapshotError,
    ReferenceSnapshotErrorCode,
    verify_reference_snapshot,
)

ROOT = Path(__file__).resolve().parents[3]
REFERENCE_MANIFEST = ROOT / "contracts" / "manifests" / "reference-embedding.json"


def test_reference_manifest_records_reviewed_immutable_identity() -> None:
    manifest = json.loads(REFERENCE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["dimension"] == 384
    assert manifest["model_declared_max_tokens"] == 512
    assert manifest["logical_model"] == {
        "repository": "BAAI/bge-small-en-v1.5",
        "revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
        "license": "MIT",
        "artifact": {
            "path": "onnx/model.onnx",
            "size_bytes": 133093490,
            "digest": {
                "algorithm": "sha256",
                "value": ("828e1496d7fabb79cfa4dcd84fa38625c0d3d21da474a00f08db0f559940cf35"),
            },
        },
    }
    runtime_model = manifest["runtime_model"]
    assert runtime_model["repository"] == "qdrant/bge-small-en-v1.5-onnx-q"
    assert runtime_model["revision"] == "52398278842ec682c6f32300af41344b1c0b0bb2"
    assert runtime_model["license"] == "Apache-2.0"
    assert {record["path"] for record in runtime_model["files"]} == {
        "config.json",
        "model_optimized.onnx",
        "ort_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    }
    model_record = next(
        record for record in runtime_model["files"] if record["path"] == "model_optimized.onnx"
    )
    assert model_record["size_bytes"] == 66465124
    assert model_record["digest"]["value"] == (
        "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"
    )
    assert manifest["runtime"]["fastembed"]["version"] == "0.8.0"
    assert manifest["runtime"]["onnxruntime"] == {
        "package": "onnxruntime",
        "version": "1.29.0",
    }
    assert manifest["runtime"]["execution_providers"] == ["CPUExecutionProvider"]
    assert manifest["runtime"]["loading"] == {
        "preverify_all_files": True,
        "specific_model_path_required": True,
        "local_files_only": True,
        "explicit_application_cache_required": True,
    }
    assert manifest["text_policy"]["query_prefix"] == ""
    assert manifest["text_policy"]["document_prefix"] == ""
    assert manifest["numeric_tolerance"]["status"] == "unmeasured"
    assert manifest["numeric_tolerance"]["cross_platform_max_absolute_delta"] is None


def _write_test_manifest(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "identity": "test-reference-v1",
                "dimension": 384,
                "runtime_model": {
                    "revision": "0000000000000000000000000000000000000001",
                    "files": records,
                },
            }
        ),
        encoding="utf-8",
    )


def test_snapshot_verification_accepts_declared_sha256_and_git_blob(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    model_content = b"model"
    config_content = b"config"
    (snapshot / "model.onnx").write_bytes(model_content)
    (snapshot / "config.json").write_bytes(config_content)
    git_blob_digest = sha1(f"blob {len(config_content)}\0".encode() + config_content).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(
        manifest_path,
        [
            {
                "path": "model.onnx",
                "size_bytes": len(model_content),
                "digest": {
                    "algorithm": "sha256",
                    "value": sha256(model_content).hexdigest(),
                },
            },
            {
                "path": "config.json",
                "size_bytes": len(config_content),
                "digest": {"algorithm": "git-sha1", "value": git_blob_digest},
            },
        ],
    )

    verified = verify_reference_snapshot(
        manifest_path=manifest_path,
        snapshot_path=snapshot,
    )

    assert verified.path == snapshot.resolve()
    assert verified.identity == "test-reference-v1"
    assert verified.dimension == 384


def test_snapshot_verification_fails_closed_on_digest_mismatch(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    content = b"changed"
    (snapshot / "model.onnx").write_bytes(content)
    manifest_path = tmp_path / "manifest.json"
    _write_test_manifest(
        manifest_path,
        [
            {
                "path": "model.onnx",
                "size_bytes": len(content),
                "digest": {"algorithm": "sha256", "value": "0" * 64},
            }
        ],
    )

    with pytest.raises(ReferenceSnapshotError) as captured:
        verify_reference_snapshot(
            manifest_path=manifest_path,
            snapshot_path=snapshot,
        )

    assert captured.value.code is ReferenceSnapshotErrorCode.SNAPSHOT_MISMATCH
