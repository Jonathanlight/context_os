"""RAG-family analyzers (category R) — Phase 6.4.

Six rules across two themes:

- **Chunking sanity** (R001, R002, R006) — flag chunk-size choices
  that produce pathological retrieval (excessive overlap, no headroom,
  large files without chunking overrides).
- **Pipeline completeness** (R003, R004, R005) — flag gaps in the
  manifest that downstream indexers can't fill in (missing freshness
  policy, missing embedding model, anchor / chunking mismatches).

All R-rules are INFO or WARNING; none are ERROR. RAG lint defects
slow the indexer or hurt retrieval quality but never crash the
pipeline outright — those crashes are caught by the AST validators
in :mod:`contextos.ast.rag`.
"""

from __future__ import annotations

from contextos.analyzers.rag import chunking_sanity, pipeline_completeness

__all__ = ["chunking_sanity", "pipeline_completeness"]
