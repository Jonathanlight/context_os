"""Analyzers: AST → diagnostics.

Phase 2 shipped the agent-family analyzers across six categories: A
(ambiguity), C (contradiction), K (completeness), X (anti-pattern),
F (LLM-friendliness), P (platform). Phase 5.4 adds the skill family
(S category). Phase 6 will add the RAG category.

An analyzer is a callable
``(payload, *, source: str | None) -> Iterable[Diagnostic]``. The
orchestrator :func:`lint_document` dispatches on ``Document.type``,
runs every registered analyzer for that flavor in deterministic order,
and returns a :class:`DiagnosticBag`.

Module-level functions rather than classes keep the surface tight.
Wrap in a class only when an analyzer needs per-call configuration.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from contextos.analyzers.agent import (
    ambiguity,
    antipattern,
    completeness,
    contradiction,
    llm_friendly,
    platform,
)
from contextos.analyzers.skill import body_coherence, description_quality
from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.skill import SkillDocument
from contextos.diagnostics import Diagnostic, DiagnosticBag

AgentAnalyzer = Callable[[AgentDocument], Iterable[Diagnostic]]
"""Type alias for agent analyzers — used by external integrations only."""

SkillAnalyzer = Callable[[SkillDocument], Iterable[Diagnostic]]
"""Type alias for skill analyzers."""

_AGENT_ANALYZERS: tuple[Callable[[AgentDocument, str | None], Iterable[Diagnostic]], ...] = (
    ambiguity.check,
    antipattern.check,
    completeness.check,
    contradiction.check,
    llm_friendly.check,
    platform.check,
)

_SKILL_ANALYZERS: tuple[Callable[[SkillDocument], Iterable[Diagnostic]], ...] = (
    description_quality.check,
    body_coherence.check,
)


def lint_document(doc: Document, *, source: str | None = None) -> DiagnosticBag:
    """Run every registered analyzer on ``doc`` and collect diagnostics.

    Dispatches on :attr:`Document.type`; only the analyzers matching
    the active flavor are invoked. The returned :class:`DiagnosticBag`
    can be iterated, rendered, or queried for pass/fail via
    :meth:`DiagnosticBag.has_errors`.
    """
    bag = DiagnosticBag()
    if doc.type == "agent" and doc.agent is not None:
        for agent_analyzer in _AGENT_ANALYZERS:
            bag.extend(agent_analyzer(doc.agent, source))
    elif doc.type == "skill" and doc.skill is not None:
        for skill_analyzer in _SKILL_ANALYZERS:
            bag.extend(skill_analyzer(doc.skill))
    return bag


__all__ = ["AgentAnalyzer", "SkillAnalyzer", "lint_document"]
