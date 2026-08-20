"""Fail-closed verification for a pre-provisioned embedding snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha1, sha256
from pathlib import Path
from typing import cast


class ReferenceSnapshotErrorCode(StrEnum):
    """Stable reasons a reference snapshot cannot be trusted."""

    INVALID_MANIFEST = "embedding.invalid_manifest"
    MISSING_FILE = "embedding.snapshot_file_missing"
    SNAPSHOT_MISMATCH = "embedding.snapshot_mismatch"


class ReferenceSnapshotError(RuntimeError):
    """A typed failure raised before any model runtime may be constructed."""

    def __init__(self, code: ReferenceSnapshotErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class VerifiedReferenceSnapshot:
    """Identity returned only after every declared runtime file is verified."""

    path: Path
    identity: str
    runtime_revision: str
    dimension: int


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            f"{field} must be an object",
        )
    return cast(dict[str, object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            f"{field} must be a non-empty string",
        )
    return value


def _integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            f"{field} must be a positive integer",
        )
    return value


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        value: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            "reference embedding manifest could not be read",
        ) from error
    return _mapping(value, "manifest")


def _digest_file(path: Path, algorithm: str, size_bytes: int) -> str:
    if algorithm == "sha256":
        digest = sha256()
    elif algorithm == "git-sha1":
        digest = sha1()
        digest.update(f"blob {size_bytes}\0".encode())
    else:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            f"unsupported digest algorithm: {algorithm}",
        )

    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_reference_snapshot(
    *, manifest_path: Path, snapshot_path: Path
) -> VerifiedReferenceSnapshot:
    """Verify all declared files before returning a usable snapshot identity."""

    manifest = _load_manifest(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            "unsupported reference embedding manifest schema",
        )

    identity = _string(manifest.get("identity"), "identity")
    dimension = _integer(manifest.get("dimension"), "dimension")
    runtime_model = _mapping(manifest.get("runtime_model"), "runtime_model")
    runtime_revision = _string(runtime_model.get("revision"), "runtime_model.revision")
    files = runtime_model.get("files")
    if not isinstance(files, list) or not files:
        raise ReferenceSnapshotError(
            ReferenceSnapshotErrorCode.INVALID_MANIFEST,
            "runtime_model.files must be a non-empty list",
        )

    resolved_root = snapshot_path.resolve()
    for index, file_value in enumerate(files):
        record = _mapping(file_value, f"runtime_model.files[{index}]")
        relative_path = Path(_string(record.get("path"), f"runtime_model.files[{index}].path"))
        size_bytes = _integer(record.get("size_bytes"), f"runtime_model.files[{index}].size_bytes")
        digest_record = _mapping(record.get("digest"), f"runtime_model.files[{index}].digest")
        algorithm = _string(
            digest_record.get("algorithm"),
            f"runtime_model.files[{index}].digest.algorithm",
        )
        expected_digest = _string(
            digest_record.get("value"),
            f"runtime_model.files[{index}].digest.value",
        )

        candidate = (resolved_root / relative_path).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError as error:
            raise ReferenceSnapshotError(
                ReferenceSnapshotErrorCode.INVALID_MANIFEST,
                f"runtime file escapes the snapshot root: {relative_path}",
            ) from error

        if not candidate.is_file():
            raise ReferenceSnapshotError(
                ReferenceSnapshotErrorCode.MISSING_FILE,
                f"required runtime file is missing: {relative_path}",
            )
        actual_size = candidate.stat().st_size
        if actual_size != size_bytes:
            raise ReferenceSnapshotError(
                ReferenceSnapshotErrorCode.SNAPSHOT_MISMATCH,
                f"runtime file size mismatch: {relative_path}",
            )
        if _digest_file(candidate, algorithm, size_bytes) != expected_digest:
            raise ReferenceSnapshotError(
                ReferenceSnapshotErrorCode.SNAPSHOT_MISMATCH,
                f"runtime file digest mismatch: {relative_path}",
            )

    return VerifiedReferenceSnapshot(
        path=resolved_root,
        identity=identity,
        runtime_revision=runtime_revision,
        dimension=dimension,
    )
