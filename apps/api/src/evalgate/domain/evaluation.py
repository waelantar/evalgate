"""Deterministic retrieval and citation metrics for reviewed evaluation cases."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def precision_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    window = retrieved[:k]
    return sum(item in relevant for item in window) / k


def recall_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return sum(item in relevant for item in retrieved[:k]) / len(relevant)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str]) -> float:
    for rank, item in enumerate(retrieved, 1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevance: dict[str, int], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    def dcg(values: Iterable[int]) -> float:
        return float(
            sum((2**gain - 1) / math.log2(rank + 2) for rank, gain in enumerate(values))
        )

    actual = dcg([relevance.get(item, 0) for item in retrieved[:k]])
    ideal = dcg(sorted(relevance.values(), reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def citation_validity(citations: Sequence[dict[str, object]], evidence_ids: set[str]) -> float:
    if not citations:
        return 0.0
    valid = sum(
        isinstance(item.get("evidence_id"), str) and item["evidence_id"] in evidence_ids
        for item in citations
    )
    return valid / len(citations)


def citation_coverage(citations: Sequence[dict[str, object]], supported_claims: set[str]) -> float:
    if not supported_claims:
        return 0.0
    claims = {item.get("claim") for item in citations}
    return len(claims & supported_claims) / len(supported_claims)
