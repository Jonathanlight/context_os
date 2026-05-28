"""Embedding-based RAG retrieval provider — Phase 7.9.

Lives in its own module so :mod:`contextos.eval` stays importable
without ``numpy``. ContextOS does **not** ship an embedding service;
the user supplies a callable that turns a query string into a vector
(typically by wrapping ``voyageai`` / ``openai`` / a local model) and
brings the corpus chunks already embedded.

The cosine similarity is computed in-process via numpy — no FAISS,
no external vector database. This keeps the dependency footprint at
just numpy and stays fast for the small-corpus case that matters
for evaluation (hundreds to thousands of chunks, not millions).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from contextos.eval.providers import TokenUsage
from contextos.eval.rag_providers import Chunk, RetrievalResponse

if TYPE_CHECKING:
    import numpy as np

EmbedQueryFn = Callable[[str], list[float]]
"""User-supplied function that embeds a query into a vector.

Must return a list[float] whose length matches the chunks' embedding
dimension. Examples (user code, not shipped):

.. code-block:: python

   # OpenAI
   def embed_openai(text: str) -> list[float]:
       resp = openai_client.embeddings.create(model="text-embedding-3-large", input=text)
       return resp.data[0].embedding

   # Voyage
   def embed_voyage(text: str) -> list[float]:
       resp = voyage_client.embed(texts=[text], model="voyage-3")
       return resp.embeddings[0]
"""


class EmbeddingRagProvider:
    """In-process cosine-similarity retriever over pre-indexed chunks.

    Construction is **eager**: we stack the chunks' vectors into a
    single matrix at init time so each ``retrieve()`` call is one
    numpy dot product, not N. The matrix lives in memory; for very
    large corpora a memory-mapped store would be better, but
    evaluation suites typically run on hundreds to a few thousand
    chunks where the in-memory cost is negligible.
    """

    def __init__(
        self,
        chunks: list[Chunk],
        embed_query: EmbedQueryFn,
    ) -> None:
        """Build the retriever from pre-indexed chunks.

        :param chunks: corpus chunks with ``source`` + ``vector``
            populated. All vectors must share the same dimension; a
            dimension mismatch raises ValueError on construction.
        :param embed_query: callable that embeds a query into the
            same vector space as the chunks. Token usage from the
            embedding call is **not** measured here — the caller
            instruments their own embedding function if they want
            cost tracking.
        """
        import numpy as np  # noqa: PLC0415 — lazy by design

        if not chunks:
            msg = "EmbeddingRagProvider requires at least one chunk"
            raise ValueError(msg)

        first_dim = len(chunks[0].vector)
        for idx, chunk in enumerate(chunks):
            if len(chunk.vector) != first_dim:
                msg = (
                    f"Chunk #{idx} ({chunk.source!r}) has embedding "
                    f"dimension {len(chunk.vector)}, expected {first_dim}"
                )
                raise ValueError(msg)

        self._chunks = list(chunks)
        self._embed_query = embed_query
        # Stack vectors into a (n_chunks, dim) matrix and pre-normalize
        # rows so cosine becomes a single matmul against a normalized
        # query vector at retrieve() time.
        matrix = np.asarray([c.vector for c in chunks], dtype=np.float64)
        self._chunk_matrix: np.ndarray = _normalize_rows(matrix, np)

    def retrieve(self, query: str, top_k: int) -> RetrievalResponse:
        """Embed ``query`` and return the top_k chunks by cosine similarity."""
        import numpy as np  # noqa: PLC0415 — lazy by design

        query_vec = self._embed_query(query)
        if len(query_vec) != self._chunk_matrix.shape[1]:
            msg = (
                f"Query embedding dim {len(query_vec)} does not match "
                f"chunk dim {self._chunk_matrix.shape[1]}"
            )
            raise ValueError(msg)
        query_arr = np.asarray(query_vec, dtype=np.float64)
        query_norm = _normalize_vector(query_arr, np)

        # Cosine == dot product on normalized vectors.
        similarities = self._chunk_matrix @ query_norm
        # argsort ascending → reverse → slice for top-k indices.
        ranked = np.argsort(similarities)[::-1][:top_k]

        return RetrievalResponse(
            retrieved_sources=[self._chunks[int(i)].source for i in ranked],
            similarities=[float(similarities[int(i)]) for i in ranked],
            token_usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


def _normalize_rows(matrix: np.ndarray, np_mod: object) -> np.ndarray:
    """L2-normalize each row of ``matrix``.

    Pure helper to keep the provider's __init__ readable. Zero-norm
    rows survive as zero rows; the cosine then evaluates to zero, which
    is the right answer for "this chunk has no signal."
    """
    import numpy as np  # noqa: PLC0415 — lazy by design

    _ = np_mod
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0, 1.0, norms)
    normalized: np.ndarray = matrix / safe_norms
    return normalized


def _normalize_vector(vector: np.ndarray, np_mod: object) -> np.ndarray:
    """L2-normalize a single vector. Same zero-norm behavior as the row variant."""
    import numpy as np  # noqa: PLC0415 — lazy by design

    _ = np_mod
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector
    normalized: np.ndarray = vector / norm
    return normalized


__all__ = ["EmbedQueryFn", "EmbeddingRagProvider"]
