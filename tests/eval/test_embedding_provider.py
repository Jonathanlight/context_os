"""Tests for the EmbeddingRagProvider — Phase 7.9."""

from __future__ import annotations

import pytest

from contextos.eval.embedding_provider import EmbeddingRagProvider
from contextos.eval.rag_providers import Chunk


def _chunk(source: str, vector: list[float]) -> Chunk:
    return Chunk(source=source, vector=vector)


def _identity_embed(text: str) -> list[float]:
    """Tiny embedding fn for tests: hash-based deterministic vector.

    Not a real embedding; we use it only to drive the cosine path
    against known geometry below.
    """
    if text == "a":
        return [1.0, 0.0, 0.0]
    if text == "b":
        return [0.0, 1.0, 0.0]
    if text == "ab":
        return [0.7, 0.7, 0.0]
    return [0.0, 0.0, 1.0]


class TestEmbeddingRagProviderConstruction:
    def test_empty_chunks_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"at least one chunk"):
            EmbeddingRagProvider(chunks=[], embed_query=_identity_embed)

    def test_dimension_mismatch_rejected(self) -> None:
        chunks = [
            _chunk("a.md", [1.0, 0.0, 0.0]),
            _chunk("b.md", [1.0, 0.0]),  # wrong dim
        ]
        with pytest.raises(ValueError, match=r"dimension"):
            EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)

    def test_construction_with_consistent_dims(self) -> None:
        chunks = [
            _chunk("a.md", [1.0, 0.0, 0.0]),
            _chunk("b.md", [0.0, 1.0, 0.0]),
        ]
        # Should not raise.
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)
        assert provider is not None


class TestEmbeddingRagProviderRetrieval:
    def test_exact_match_ranks_first(self) -> None:
        chunks = [
            _chunk("a.md", [1.0, 0.0, 0.0]),
            _chunk("b.md", [0.0, 1.0, 0.0]),
        ]
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)
        response = provider.retrieve("a", top_k=2)
        assert response.retrieved_sources[0] == "a.md"
        assert response.similarities[0] > response.similarities[1]

    def test_top_k_truncates_output(self) -> None:
        chunks = [
            _chunk("a.md", [1.0, 0.0, 0.0]),
            _chunk("b.md", [0.0, 1.0, 0.0]),
            _chunk("c.md", [0.0, 0.0, 1.0]),
        ]
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)
        response = provider.retrieve("a", top_k=2)
        assert len(response.retrieved_sources) == 2

    def test_query_dim_mismatch_rejected(self) -> None:
        chunks = [_chunk("a.md", [1.0, 0.0, 0.0])]

        def wrong_dim_embed(text: str) -> list[float]:
            return [1.0, 0.0]  # 2-d, but chunks are 3-d

        provider = EmbeddingRagProvider(chunks=chunks, embed_query=wrong_dim_embed)
        with pytest.raises(ValueError, match=r"dim"):
            provider.retrieve("anything", top_k=1)

    def test_blended_query_picks_closest(self) -> None:
        chunks = [
            _chunk("a.md", [1.0, 0.0, 0.0]),
            _chunk("b.md", [0.0, 1.0, 0.0]),
        ]
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)
        # Query "ab" embeds to [0.7, 0.7, 0]. Cosine is equal vs a and b,
        # so the order is implementation-defined; both should appear in
        # top-2 and similarities should be ~equal.
        response = provider.retrieve("ab", top_k=2)
        assert set(response.retrieved_sources) == {"a.md", "b.md"}
        # Similarities should be approximately equal (both ~0.707).
        assert abs(response.similarities[0] - response.similarities[1]) < 0.01

    def test_zero_vectors_dont_crash(self) -> None:
        chunks = [
            _chunk("a.md", [0.0, 0.0, 0.0]),
            _chunk("b.md", [1.0, 0.0, 0.0]),
        ]
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=_identity_embed)
        response = provider.retrieve("a", top_k=2)
        # Zero-norm chunk evaluates to similarity 0; non-zero chunk wins.
        assert response.retrieved_sources[0] == "b.md"
