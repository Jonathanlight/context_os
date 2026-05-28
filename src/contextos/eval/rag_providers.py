"""RAG retrieval providers — Phase 7.9.

Mirrors the Skills-side architecture from Phase 7.8: a Protocol that
every backend implements, a deterministic Mock for tests, and a real
implementation in a separate module that owns the heavy dependency.

The real implementation lives in
:mod:`contextos.eval.embedding_provider`. It depends on ``numpy`` for
the cosine computation and is exposed under the ``[eval]`` extras.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from contextos.eval.providers import TokenUsage


class Chunk(BaseModel):
    """One pre-indexed chunk that the retrieval provider scores.

    ``source`` is the human-meaningful identifier (path) the eval
    suite's ``expected_sources`` matches against — typically the file
    or section the chunk came from. ``vector`` is the chunk's
    pre-computed embedding (length must match the query embedding).
    ``content`` is optional debug context never used by the scoring
    path; it surfaces only in the rendered report when the user wants
    to see *what* the retrieval pulled.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    vector: list[float] = Field(min_length=1)
    content: str | None = None


class RetrievalResponse(BaseModel):
    """Provider's response for one :class:`~contextos.ast.eval.RagCase`."""

    model_config = ConfigDict(extra="forbid")

    retrieved_sources: list[str] = Field(default_factory=list)
    similarities: list[float] = Field(
        default_factory=list,
        description=(
            "Cosine (or other) similarity scores, parallel to "
            "``retrieved_sources``. Optional — the mock provider "
            "returns an empty list and the runner does not score on "
            "similarity, only on whether expected sources hit."
        ),
    )
    token_usage: TokenUsage | None = None


class RagRetrievalProvider(Protocol):
    """The shape every RAG retrieval backend must satisfy.

    Implementations:

    - :class:`MockRagProvider` for tests (deterministic, zero-cost).
    - :class:`~contextos.eval.embedding_provider.EmbeddingRagProvider`
      for production runs (real embedding API + numpy cosine).

    Backends supply their own embedding service; ContextOS does not
    ship one. The user injects a callable that turns a query into a
    vector, and supplies the corpus chunks already embedded.
    """

    def retrieve(self, query: str, top_k: int) -> RetrievalResponse: ...


class MockRagProvider:
    """Deterministic provider that looks queries up in a table.

    Used exclusively by tests. The runner's pass-fail logic, top_k
    behavior, and aggregate accounting are validated against this
    mock so a real-API run only adds the embedding / cosine path on
    top of an already-tested orchestration layer.
    """

    def __init__(
        self,
        retrieval_table: dict[str, list[str]],
        *,
        default: list[str] | None = None,
        error_for: frozenset[str] | None = None,
    ) -> None:
        """Build a mock provider.

        :param retrieval_table: query → list of retrieved source paths
            (already ordered by relevance, length up to caller).
        :param default: fallback for queries not in the table.
        :param error_for: queries that should raise instead of
            returning a response.
        """
        self._table = {q: list(sources) for q, sources in retrieval_table.items()}
        self._default = list(default) if default is not None else []
        self._error_for = error_for or frozenset()

    def retrieve(self, query: str, top_k: int) -> RetrievalResponse:
        """Return the configured response for ``query`` truncated to ``top_k``."""
        if query in self._error_for:
            msg = f"MockRagProvider configured to error on query: {query!r}"
            raise RuntimeError(msg)
        sources = self._table.get(query, self._default)[:top_k]
        return RetrievalResponse(
            retrieved_sources=sources,
            similarities=[],
            token_usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


__all__ = [
    "Chunk",
    "MockRagProvider",
    "RagRetrievalProvider",
    "RetrievalResponse",
]
