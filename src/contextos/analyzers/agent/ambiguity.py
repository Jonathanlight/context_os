"""Ambiguity analyzers (category A) — vague directives, subjective wording.

Phase 2.0 ships A001 only. Later milestones add A002 (subjective
adjectives) through A005 (fuzzy quantifiers).
"""

from __future__ import annotations

from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# Vague directives the LLM cannot operationalize. Each entry is a normalized
# (lowercase, no trailing punctuation) phrase. Match is by equality or by
# "starts-with + space" so "Be concise about errors" still flags.
_VAGUE_DIRECTIVES = frozenset(
    {
        "be concise",
        "be careful",
        "be clear",
        "be nice",
        "be smart",
        "write clean code",
        "write good code",
        "use good naming",
        "use proper naming",
        "avoid bad practices",
        "follow best practices",
        "make it nice",
        "make it clean",
        "make it simple",
        "keep it simple",
        "keep it clean",
        "do the right thing",
    }
)

A001_CODE = "A001"
A001_SEVERITY = DiagSeverity.WARNING
A001_DOC_URL = "https://contextos.dev/rules/A001"


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every A* check against ``agent``."""
    _ = source  # reserved for future rules that need file-relative context
    for rule in agent.rules:
        yield from _check_vague_directive(rule)


def _check_vague_directive(rule: Rule) -> Iterable[Diagnostic]:
    """A001 — flag a rule whose title is a known vague directive."""
    normalized = rule.title.strip().lower().rstrip(".")
    if normalized in _VAGUE_DIRECTIVES or any(
        normalized.startswith(f"{directive} ") for directive in _VAGUE_DIRECTIVES
    ):
        yield Diagnostic(
            code=A001_CODE,
            severity=A001_SEVERITY,
            message=f"vague directive: '{rule.title}'",
            position=rule.position,
            suggestion=(
                "rephrase with a measurable criterion "
                "(e.g. 'public functions <= 40 lines' instead of 'be concise')"
            ),
            doc_url=A001_DOC_URL,
        )
