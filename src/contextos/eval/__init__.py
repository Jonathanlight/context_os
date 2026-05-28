"""Live evaluation runners for ContextOS — Phase 7B.

The lint pipeline (Phases 2 / 5.4 / 6.4) validates *structure*. This
module adds *functional* evaluation: actually invoke an LLM with the
skill registry attached, see which skill the model picks, and score
the result against the expected routing.

The :class:`SkillEvalRunner` and providers below cover Phase 7.8 (the
Anthropic Skills routing family). Phase 7.9 will add a parallel
``RagEvalRunner`` over an embedding-similarity provider.

Optional dependency: the Anthropic provider requires the ``[eval]``
extras (``pipx install context-os[eval]``). The Mock provider and the
runner have no third-party deps and stay importable without the
extras — that's the surface tests use.
"""

from __future__ import annotations

from contextos.eval.providers import (
    MockSkillProvider,
    RoutingResponse,
    SkillRoutingProvider,
    TokenUsage,
)
from contextos.eval.results import EvalCaseResult, EvalRunResult
from contextos.eval.runner import SkillEvalRunner

__all__ = [
    "EvalCaseResult",
    "EvalRunResult",
    "MockSkillProvider",
    "RoutingResponse",
    "SkillEvalRunner",
    "SkillRoutingProvider",
    "TokenUsage",
]
