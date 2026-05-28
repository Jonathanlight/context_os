"""Live evaluation runners for ContextOS — Phase 7B.

The lint pipeline (Phases 2 / 5.4 / 6.4) validates *structure*. This
module adds *functional* evaluation: actually invoke an LLM with the
skill registry attached, see which skill the model picks, and score
the result against the expected routing.

Two evaluators ship today:

- :class:`SkillEvalRunner` (Phase 7.8) — Anthropic Skills routing
  via the Messages API tool-use feature.
- :class:`RagEvalRunner` (Phase 7.9) — RAG retrieval via cosine
  similarity over pre-indexed embeddings.

Both follow the same shape: a Protocol the backend implements, a
Mock for tests, and a real backend module that owns the heavy dep
(``anthropic`` for Skills, ``numpy`` for RAG cosine). The user
provides their own embedding service for the RAG case — ContextOS
does not ship one.

Optional dependency: ``[eval]`` extras (``anthropic`` + ``numpy``).
The Mock providers and runners have no third-party deps and stay
importable without the extras — that's the surface tests use.
"""

from __future__ import annotations

from contextos.eval.diff import (
    CaseChange,
    EvalDiff,
    compute_eval_diff,
)
from contextos.eval.providers import (
    MockSkillProvider,
    RoutingResponse,
    SkillRoutingProvider,
    TokenUsage,
)
from contextos.eval.rag_providers import (
    Chunk,
    MockRagProvider,
    RagRetrievalProvider,
    RetrievalResponse,
)
from contextos.eval.rag_runner import RagEvalRunner
from contextos.eval.results import EvalCaseResult, EvalRunResult
from contextos.eval.runner import SkillEvalRunner

__all__ = [
    "CaseChange",
    "Chunk",
    "EvalCaseResult",
    "EvalDiff",
    "EvalRunResult",
    "MockRagProvider",
    "MockSkillProvider",
    "RagEvalRunner",
    "RagRetrievalProvider",
    "RetrievalResponse",
    "RoutingResponse",
    "SkillEvalRunner",
    "SkillRoutingProvider",
    "TokenUsage",
    "compute_eval_diff",
]
