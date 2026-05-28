"""Unit tests for the RAG providers — Phase 7.9."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.eval.rag_providers import (
    Chunk,
    MockRagProvider,
    RetrievalResponse,
)


class TestChunk:
    def test_minimal_chunk(self) -> None:
        chunk = Chunk(source="docs/x.md", vector=[0.1, 0.2, 0.3])
        assert chunk.source == "docs/x.md"
        assert chunk.content is None

    def test_empty_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(source="", vector=[1.0])

    def test_empty_vector_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(source="x", vector=[])


class TestMockRagProvider:
    def test_returns_table_entry(self) -> None:
        provider = MockRagProvider({"what is X?": ["docs/x.md", "docs/other.md"]})
        response = provider.retrieve("what is X?", top_k=5)
        assert response.retrieved_sources == ["docs/x.md", "docs/other.md"]

    def test_top_k_truncates(self) -> None:
        provider = MockRagProvider({"q": ["a", "b", "c", "d", "e"]})
        response = provider.retrieve("q", top_k=2)
        assert response.retrieved_sources == ["a", "b"]

    def test_unknown_query_uses_default(self) -> None:
        provider = MockRagProvider({}, default=["fallback.md"])
        response = provider.retrieve("unknown", top_k=5)
        assert response.retrieved_sources == ["fallback.md"]

    def test_no_default_returns_empty(self) -> None:
        provider = MockRagProvider({})
        response = provider.retrieve("unknown", top_k=5)
        assert response.retrieved_sources == []

    def test_raises_on_error_set(self) -> None:
        provider = MockRagProvider({}, error_for=frozenset({"crash"}))
        with pytest.raises(RuntimeError, match=r"configured to error"):
            provider.retrieve("crash", top_k=5)

    def test_token_usage_is_zero(self) -> None:
        provider = MockRagProvider({"q": ["x"]})
        response = provider.retrieve("q", top_k=5)
        assert response.token_usage is not None
        assert response.token_usage.total == 0


class TestRetrievalResponse:
    def test_default_response_is_empty(self) -> None:
        resp = RetrievalResponse()
        assert resp.retrieved_sources == []
        assert resp.similarities == []
        assert resp.token_usage is None
