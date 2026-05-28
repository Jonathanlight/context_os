"""Pydantic models for the **rag** family — Phase 6.

A RAG corpus declaration is a `.ctx` source carrying a single ``[rag]``
table that configures the retrieval pipeline (chunking, embedding,
reranking, freshness) and a list of ``[[document]]`` entries that
describe the source files to index.

ContextOS does **not** execute the pipeline — it only parses, lints,
audits, and emits a manifest for downstream indexers (Qdrant, Pinecone,
custom implementations) to consume. The ``vector_store``, ``embedding_model``,
and ``reranker`` fields are intentionally free-form strings: the SPEC
pins their **purpose**, not their **values**, so a new vendor name
doesn't require a parser change.

Phase 6.1 lands the AST only. The `.ctx` parser extension, manifest
emitter, RAG analyzers (R001+), and CLI integration ship in 6.2 / 6.3
/ 6.4 / 6.5 respectively.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ChunkingStrategy = Literal["fixed", "semantic", "header_aware"]
"""Allowed values for :attr:`RagConfig.chunking_strategy`.

Mirrors SPEC §1.4.1. Adding a strategy is a single literal expansion
that ripples through every match statement on this type.
"""

FRESHNESS_PATTERN = r"^\d+[dwmy]$"
"""Compact freshness format: integer + unit (``d`` / ``w`` / ``m`` / ``y``).

Checked by Pydantic via :class:`StringConstraints`. Examples:
``7d`` (one week), ``30d`` (one month), ``1y`` (one year). A free-form
ISO 8601 duration would be more expressive but harder to compare; the
compact form matches the shapes real-world indexers use.
"""

_FRESHNESS_REGEX = re.compile(FRESHNESS_PATTERN)

CHUNK_MIN_TOKENS_FLOOR = 50
"""Lower bound for any chunk-size field.

Chunks below ~50 tokens carry too little context for retrieval to be
useful — they fragment ideas across boundaries and force the reranker
to assemble tiny pieces.
"""

CHUNK_MAX_TOKENS_CEILING = 4000
"""Upper bound for any chunk-size field.

Beyond ~4000 tokens, a single chunk approaches a small LLM's full
context window and defeats the point of retrieval.
"""

TOP_K_CEILING = 100
"""Upper bound for ``retrieval_top_k`` / ``reranking_top_k``.

Past 100, the reranker cost outweighs precision gains. A future ceiling
revision should track reranker benchmarks; for now this is a safe
heuristic.
"""

FreshnessPolicy = Annotated[str, StringConstraints(pattern=FRESHNESS_PATTERN)]
LanguageCode = Annotated[str, StringConstraints(min_length=2, max_length=8)]
"""Lower-case BCP-47 language tag (``fr``, ``en``, ``pt-BR``).

We don't check against a registry — that list churns and an unknown
tag is recoverable. The min/max bounds catch typos.
"""


class RagConfig(BaseModel):
    """Pipeline configuration for a RAG corpus.

    Field order matches SPEC §1.4.1. All chunk-size fields are bounded
    on the AST so a typo (``chunk_target_tokens = 5000000``) surfaces
    as a model error rather than as a runtime mystery in the indexer.
    """

    model_config = ConfigDict(extra="forbid")

    chunking_strategy: ChunkingStrategy = "semantic"
    chunk_target_tokens: int = Field(
        default=500,
        ge=CHUNK_MIN_TOKENS_FLOOR,
        le=CHUNK_MAX_TOKENS_CEILING,
    )
    chunk_overlap_tokens: int = Field(
        default=50,
        ge=0,
        le=CHUNK_MAX_TOKENS_CEILING,
    )
    chunk_min_tokens: int = Field(
        default=100,
        ge=CHUNK_MIN_TOKENS_FLOOR,
        le=CHUNK_MAX_TOKENS_CEILING,
    )
    chunk_max_tokens: int = Field(
        default=1500,
        ge=CHUNK_MIN_TOKENS_FLOOR,
        le=CHUNK_MAX_TOKENS_CEILING,
    )
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(default=None, ge=1, le=16384)
    vector_store: str | None = None
    reranker: str | None = None
    retrieval_top_k: int = Field(default=10, ge=1, le=TOP_K_CEILING)
    reranking_top_k: int = Field(default=3, ge=1, le=TOP_K_CEILING)
    freshness_policy: FreshnessPolicy | None = None
    language_default: LanguageCode | None = None

    @model_validator(mode="after")
    def _check_chunk_size_ordering(self) -> RagConfig:
        """Enforce ``chunk_min <= chunk_target <= chunk_max``.

        The pipeline degenerates when these are out of order:
        ``chunk_min > chunk_target`` makes the chunker reject every
        chunk it produces; ``chunk_target > chunk_max`` does the same
        from the other end. Catch it once, at AST construction time.
        """
        if self.chunk_min_tokens > self.chunk_target_tokens:
            msg = (
                f"chunk_min_tokens ({self.chunk_min_tokens}) cannot exceed "
                f"chunk_target_tokens ({self.chunk_target_tokens})"
            )
            raise ValueError(msg)
        if self.chunk_target_tokens > self.chunk_max_tokens:
            msg = (
                f"chunk_target_tokens ({self.chunk_target_tokens}) cannot "
                f"exceed chunk_max_tokens ({self.chunk_max_tokens})"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_rerank_does_not_exceed_retrieval(self) -> RagConfig:
        """Enforce ``reranking_top_k <= retrieval_top_k``.

        The reranker scores the retrieval results; asking it to score
        more results than retrieval produced is nonsensical and almost
        always a typo.
        """
        if self.reranking_top_k > self.retrieval_top_k:
            msg = (
                f"reranking_top_k ({self.reranking_top_k}) cannot exceed "
                f"retrieval_top_k ({self.retrieval_top_k})"
            )
            raise ValueError(msg)
        return self


class DocumentEntry(BaseModel):
    """One ``[[document]]`` source declaration.

    The ``source`` field is a glob the indexer expands at run time; we
    do not resolve it here. The optional ``chunking_override`` lets
    one source override the corpus-wide ``RagConfig.chunking_strategy``
    (useful for header-rich Markdown next to plain-text legal copy).
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    freshness_required: FreshnessPolicy | None = None
    chunking_override: ChunkingStrategy | None = None
    required_anchors: list[str] = Field(default_factory=list)
    max_size_kb: int | None = Field(default=None, ge=1, le=100_000)
    language: LanguageCode | None = None


class RagDocument(BaseModel):
    """Root of the RAG family — config plus one or more document entries."""

    model_config = ConfigDict(extra="forbid")

    config: RagConfig
    documents: list[DocumentEntry] = Field(default_factory=list)


def is_valid_freshness(value: str) -> bool:
    """Helper for downstream code that wants a quick freshness check."""
    return bool(_FRESHNESS_REGEX.fullmatch(value))


__all__ = [
    "CHUNK_MAX_TOKENS_CEILING",
    "CHUNK_MIN_TOKENS_FLOOR",
    "FRESHNESS_PATTERN",
    "TOP_K_CEILING",
    "ChunkingStrategy",
    "DocumentEntry",
    "FreshnessPolicy",
    "LanguageCode",
    "RagConfig",
    "RagDocument",
    "is_valid_freshness",
]
