"""Governed-corpus invariants independent of model provisioning."""

from __future__ import annotations

import pytest

from evalgate.adapters.bundled_corpus import chunk_declared_corpus, load_declared_corpus_by_key
from evalgate.domain.corpus import IngestionError, IngestionErrorCode


class WhitespaceTokenizer:
    """Truthful test stand-in for boundary mechanics; never a production provider."""

    def token_count(self, texts: list[str]) -> int:
        return len(texts[0].split())


def test_bundled_corpus_has_reconstructive_h2_chunks() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")
    chunked = chunk_declared_corpus(corpus, tokenizer=WhitespaceTokenizer())
    documents = {document.source_key: document for document in corpus.documents}

    assert len(corpus.documents) == 20
    assert 150 <= len(chunked.chunks) <= 400
    assert all(0 < chunk.token_count <= 512 for chunk in chunked.chunks)
    assert all(
        documents[chunk.source_key].content[chunk.source_start : chunk.source_end] == chunk.content
        for chunk in chunked.chunks
    )


def test_zero_token_count_is_rejected() -> None:
    corpus = load_declared_corpus_by_key("northstar-operations")

    class ZeroTokenizer:
        def token_count(self, texts: list[str]) -> int:
            return 0

    with pytest.raises(IngestionError) as captured:
        chunk_declared_corpus(corpus, tokenizer=ZeroTokenizer())

    assert captured.value.code is IngestionErrorCode.CORPUS_INVALID
