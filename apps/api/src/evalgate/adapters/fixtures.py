"""Explicit deterministic fixtures for contract and mechanics tests only."""

from __future__ import annotations

import json
from collections.abc import Sequence
from hashlib import sha256, shake_256

from evalgate.domain.providers import (
    EmbeddingInput,
    EmbeddingVector,
    GenerationInput,
    GenerationOutput,
    ProviderIdentity,
    ProviderMode,
)

FIXTURE_EMBEDDING_DIMENSION = 384


class DeterministicEmbeddingFixture:
    """Return stable non-semantic vectors labeled as fixture output."""

    identity = ProviderIdentity(
        mode=ProviderMode.FIXTURE,
        name="evalgate-deterministic-embedding-fixture",
        revision="1",
    )
    dimension = FIXTURE_EMBEDDING_DIMENSION

    async def embed(self, inputs: Sequence[EmbeddingInput]) -> tuple[EmbeddingVector, ...]:
        vectors: list[EmbeddingVector] = []
        for item in inputs:
            digest = shake_256(
                b"evalgate-fixture-embedding-v1\x00" + item.text.encode("utf-8")
            ).digest(self.dimension)
            values = tuple((byte - 128) / 128.0 for byte in digest)
            vectors.append(EmbeddingVector(values=values, identity=self.identity))
        return tuple(vectors)


class DeterministicGenerationFixture:
    """Return stable labeled text without pretending to be model output."""

    identity = ProviderIdentity(
        mode=ProviderMode.FIXTURE,
        name="evalgate-deterministic-generation-fixture",
        revision="1",
    )

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        fingerprint = sha256(request.text.encode("utf-8")).hexdigest()[:16]
        return GenerationOutput(
            text=f"[fixture:{fingerprint}] deterministic mechanics response",
            identity=self.identity,
        )


class DeterministicGroundedAnswerFixture:
    """Return schema-valid grounded-answer mechanics output from a structured prompt."""

    identity = ProviderIdentity(
        mode=ProviderMode.FIXTURE,
        name="evalgate-deterministic-grounded-answer-fixture",
        revision="1",
    )

    async def generate(self, request: GenerationInput) -> GenerationOutput:
        payload = json.loads(request.text)
        evidence = payload["evidence"]
        output: dict[str, object]
        if not isinstance(evidence, list) or not evidence:
            output = {
                "status": "insufficient_support",
                "answer": "[fixture] The supplied evidence is insufficient.",
                "citations": [],
            }
        else:
            evidence_id = evidence[0]["evidence_id"]
            answer = "[fixture] Deterministic grounded-answer mechanics response."
            output = {
                "status": "answered",
                "answer": answer,
                "citations": [
                    {
                        "answer_start": 0,
                        "answer_end": len(answer),
                        "evidence_ids": [evidence_id],
                    }
                ],
            }
        return GenerationOutput(
            text=json.dumps(output, separators=(",", ":"), sort_keys=True),
            identity=self.identity,
        )
