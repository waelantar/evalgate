"""Offline safety tests for explicit reference-snapshot provisioning."""

from __future__ import annotations

import importlib.util
import json
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROVISION_SCRIPT = REPOSITORY_ROOT / "scripts" / "provision_reference_snapshot.py"


class _Provisioner(Protocol):
    def provision(self, *, destination: Path, manifest_path: Path) -> None: ...


def _load_provisioner() -> _Provisioner:
    spec = importlib.util.spec_from_file_location("evalgate_snapshot_provisioner", PROVISION_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("snapshot provisioner could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(_Provisioner, module)


def _write_manifest(path: Path, payload: bytes) -> None:
    path.write_text(
        json.dumps(
            {
                "runtime_model": {
                    "repository": "example/reviewed-runtime",
                    "revision": "reviewed-revision",
                    "files": [
                        {
                            "path": "model.bin",
                            "size_bytes": len(payload),
                            "digest": {
                                "algorithm": "sha256",
                                "value": sha256(payload).hexdigest(),
                            },
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )


def test_provision_publishes_verified_snapshot_and_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_provisioner()
    payload = b"reviewed snapshot"
    manifest = tmp_path / "manifest.json"
    destination = tmp_path / "snapshot"
    _write_manifest(manifest, payload)
    requested_urls: list[str] = []

    def download(url: str, target: Path) -> None:
        requested_urls.append(url)
        target.write_bytes(payload)

    monkeypatch.setattr(module, "_download", download)
    module.provision(destination=destination, manifest_path=manifest)

    assert (destination / "model.bin").read_bytes() == payload
    assert requested_urls == [
        "https://huggingface.co/example/reviewed-runtime/resolve/reviewed-revision/model.bin"
    ]
    assert not tuple(tmp_path.glob("snapshot.staging-*"))
    with pytest.raises(SystemExit, match="destination already exists"):
        module.provision(destination=destination, manifest_path=manifest)
    assert (destination / "model.bin").read_bytes() == payload


def test_digest_mismatch_cleans_owned_staging_and_allows_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_provisioner()
    payload = b"good"
    manifest = tmp_path / "manifest.json"
    destination = tmp_path / "snapshot"
    _write_manifest(manifest, payload)

    def mismatched_download(url: str, target: Path) -> None:
        del url
        target.write_bytes(b"evil")

    monkeypatch.setattr(module, "_download", mismatched_download)
    with pytest.raises(SystemExit, match="did not match"):
        module.provision(destination=destination, manifest_path=manifest)

    assert not destination.exists()
    assert not tuple(tmp_path.glob("snapshot.staging-*"))

    def reviewed_download(url: str, target: Path) -> None:
        del url
        target.write_bytes(payload)

    monkeypatch.setattr(module, "_download", reviewed_download)
    module.provision(destination=destination, manifest_path=manifest)
    assert (destination / "model.bin").read_bytes() == payload
