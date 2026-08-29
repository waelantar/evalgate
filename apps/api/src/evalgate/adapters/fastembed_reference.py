"""Fail-closed local FastEmbed adapter for the reviewed reference snapshot."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any

from evalgate.adapters.reference_embedding import ReferenceSnapshotError, verify_reference_snapshot
from evalgate.domain.corpus import IngestionError, IngestionErrorCode
from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    ProviderIdentity,
    ProviderMode,
)


class FastEmbedReferenceEmbedding:
    """Embed only through a pre-verified local snapshot and CPU execution provider."""

    def __init__(
        self,
        *,
        runtime: Any,
        identity: ProviderIdentity,
        dimension: int,
        model: str,
        revision: str,
        checksum: str,
    ) -> None:
        self._runtime = runtime
        self.identity = identity
        self.dimension = dimension
        self.model = model
        self.revision = revision
        self.checksum = checksum

    def token_count(self, texts: Sequence[str]) -> int:
        try:
            return int(self._runtime.token_count(texts))
        except Exception as error:
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                "reference tokenizer is unavailable",
            ) from error

    @classmethod
    def from_verified_snapshot(
        cls, *, manifest_path: Path, snapshot_path: Path
    ) -> FastEmbedReferenceEmbedding:
        """Verify every declared file before constructing FastEmbed; never download."""

        try:
            verified = verify_reference_snapshot(
                manifest_path=manifest_path, snapshot_path=snapshot_path
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            runtime_model = manifest["runtime_model"]
            package = manifest["runtime"]["fastembed"]
            runtime_policy = manifest["runtime"]
            if (
                package["version"] != "0.8.0"
                or version("fastembed") != "0.8.0"
                or version("onnxruntime") != "1.29.0"
                or verified.dimension != 384
                or runtime_policy["execution_providers"] != ["CPUExecutionProvider"]
                or runtime_policy["loading"]
                != {
                    "preverify_all_files": True,
                    "specific_model_path_required": True,
                    "local_files_only": True,
                    "explicit_application_cache_required": True,
                }
            ):
                raise ValueError("unexpected FastEmbed version")
            from fastembed import TextEmbedding

            cache_dir = verified.path.parent / "fastembed-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            runtime = TextEmbedding(
                model_name=manifest["logical_model"]["repository"],
                providers=["CPUExecutionProvider"],
                specific_model_path=str(verified.path),
                local_files_only=True,
                cache_dir=str(cache_dir),
            )
            model_file = next(
                item
                for item in runtime_model["files"]
                if item["path"] == runtime_model["model_file"]
            )
            if model_file["digest"]["algorithm"] != "sha256":
                raise ValueError("unexpected model digest")
        except (
            ReferenceSnapshotError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            ValueError,
            StopIteration,
            TypeError,
        ) as error:
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                "verified local reference embedding snapshot is unavailable",
            ) from error
        except ImportError as error:
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                "reference embedding runtime is unavailable",
            ) from error
        except Exception as error:
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                "reference embedding runtime is unavailable",
            ) from error
        return cls(
            runtime=runtime,
            identity=ProviderIdentity(
                mode=ProviderMode.REFERENCE,
                name=manifest["identity"],
                revision=verified.runtime_revision,
            ),
            dimension=verified.dimension,
            model=runtime_model["repository"],
            revision=verified.runtime_revision,
            checksum=model_file["digest"]["value"],
        )

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        """Return only finite 384-dimensional document/query vectors from the local runtime."""

        values = await asyncio.to_thread(self._embed_sync, tuple(item.text for item in inputs))
        if any(
            len(vector) != self.dimension or any(not math.isfinite(value) for value in vector)
            for vector in values
        ):
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_INVALID,
                "reference embedding runtime returned an unexpected dimension",
            )
        return tuple(EmbeddingVector(values=vector, identity=self.identity) for vector in values)

    def _embed_sync(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        try:
            return tuple(
                tuple(float(value) for value in vector) for vector in self._runtime.embed(texts)
            )
        except Exception as error:
            raise IngestionError(
                IngestionErrorCode.REFERENCE_EMBEDDING_UNAVAILABLE,
                "reference embedding runtime failed",
            ) from error
