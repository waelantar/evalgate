"""Explicit operator-only provisioning of the immutable FastEmbed runtime snapshot."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import urllib.request
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any


def digest(path: Path, algorithm: str, size: int) -> str:
    raw = path.read_bytes()
    if algorithm == "sha256":
        return sha256(raw).hexdigest()
    if algorithm == "git-sha1":
        return sha1(f"blob {size}\0".encode() + raw).hexdigest()
    raise ValueError("unsupported snapshot digest algorithm")


def _download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url, timeout=30) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def provision(*, destination: Path, manifest_path: Path) -> None:
    """Download, verify, and atomically publish one immutable local snapshot."""

    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime: dict[str, Any] = manifest["runtime_model"]
    destination = destination.resolve()
    if destination.exists():
        raise SystemExit("destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f"{destination.name}.staging-", dir=destination.parent)
    )
    try:
        for record in runtime["files"]:
            target = staging / record["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            url = (
                f"https://huggingface.co/{runtime['repository']}/resolve/"
                f"{runtime['revision']}/{record['path']}"
            )
            _download(url, target)
            if (
                target.stat().st_size != record["size_bytes"]
                or digest(target, record["digest"]["algorithm"], record["size_bytes"])
                != record["digest"]["value"]
            ):
                raise SystemExit("downloaded reference snapshot did not match the reviewed manifest")
        staging.replace(destination)
    except BaseException:
        # This run owns the unique staging directory; trusted destinations are never removed.
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    provision(
        destination=args.destination,
        manifest_path=root / "contracts/manifests/reference-embedding.json",
    )


if __name__ == "__main__":
    main()
