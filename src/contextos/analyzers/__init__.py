"""Analyzers: AST → diagnostics.

Phase 2 (Milestone 2.0+) ships the agent-family analyzers across six
categories: A (ambiguity), C (contradiction), K (completeness), X
(anti-pattern), F (LLM-friendliness), P (platform). Phase 5 / 6 add the
skill and RAG categories.

An analyzer is a callable
``(agent: AgentDocument, *, source: str | None) -> Iterable[Diagnostic]``.
The orchestrator :func:`lint_document` runs every registered analyzer
in deterministic order and returns a :class:`DiagnosticBag`.

Module-level functions rather than classes keep the surface tight. Wrap
in a class only when an analyzer needs per-call configuration.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from contextos.analyzers.agent import ambiguity, completeness, llm_friendly
from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.diagnostics import Diagnostic, DiagnosticBag

AgentAnalyzer = Callable[[AgentDocument], Iterable[Diagnostic]]
"""Type alias: an agent analyzer takes the agent submodel and yields diagnostics.

The ``source`` keyword argument is bound by :func:`lint_document` before the
callable is invoked, so individual analyzers do not need to thread the file
path through their internal helpers.
"""

_AGENT_ANALYZERS: tuple[Callable[[AgentDocument, str | None], Iterable[Diagnostic]], ...] = (
    ambiguity.check,
    completeness.check,
    llm_friendly.check,
)


def lint_document(doc: Document, *, source: str | None = None) -> DiagnosticBag:
    """Run every registered analyzer on ``doc`` and collect diagnostics.

    Returns a :class:`DiagnosticBag`; callers can iterate, render via the
    diagnostics renderers, or compute a pass/fail with
    :meth:`DiagnosticBag.has_errors`.
    """
    bag = DiagnosticBag()
    if doc.agent is not None:
        for analyzer in _AGENT_ANALYZERS:
            bag.extend(analyzer(doc.agent, source))
    return bag


__all__ = ["AgentAnalyzer", "lint_document"]
