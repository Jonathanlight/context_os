"""Completeness analyzers (category K) — missing sections, undocumented behaviour.

The K rules flag gaps that hurt the LLM's ability to follow the file:
no rules at all, ``must`` rules without justification, ``must`` rules
without examples. They are quieter than A and F — typically WARNING for
the structural gaps, INFO for the example-coverage hint.
"""

from __future__ import annotations

from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Severity
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# K001 — no rules declared
# ---------------------------------------------------------------------------

K001_CODE = "K001"
K001_SEVERITY = DiagSeverity.WARNING
K001_DOC_URL = "https://contextos.dev/rules/K001"

# ---------------------------------------------------------------------------
# K002 — must-rule without rationale
# ---------------------------------------------------------------------------

K002_CODE = "K002"
K002_SEVERITY = DiagSeverity.WARNING
K002_DOC_URL = "https://contextos.dev/rules/K002"

# ---------------------------------------------------------------------------
# K003 — must-rule without examples
# ---------------------------------------------------------------------------

K003_CODE = "K003"
K003_SEVERITY = DiagSeverity.INFO
K003_DOC_URL = "https://contextos.dev/rules/K003"


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every K* check against ``agent``."""
    _ = source
    yield from _check_no_rules(agent)
    for rule in agent.rules:
        yield from _check_must_without_rationale(rule)
        yield from _check_must_without_examples(rule)


def _check_no_rules(agent: AgentDocument) -> Iterable[Diagnostic]:
    """K001 — flag an AgentDocument with no rules at all.

    A context file with zero rules either forgot the section or is using
    the wrong artifact type. Both are worth surfacing; neither is fatal.
    """
    if agent.rules:
        return
    yield Diagnostic(
        code=K001_CODE,
        severity=K001_SEVERITY,
        message="agent declares no rules — the [[rules]] section is empty or missing",
        suggestion=("add at least one rule under [[rules]] to give the LLM operational guidance"),
        doc_url=K001_DOC_URL,
    )


def _check_must_without_rationale(rule: Rule) -> Iterable[Diagnostic]:
    """K002 — a ``must`` rule lacks a rationale.

    ``should`` and ``may`` rules carry implicit flexibility; ``must`` rules
    are absolute and benefit most from a written justification. The LLM
    uses the rationale when it has to weigh competing rules.
    """
    if rule.severity != Severity.MUST:
        return
    if rule.rationale is not None and rule.rationale.strip():
        return
    yield Diagnostic(
        code=K002_CODE,
        severity=K002_SEVERITY,
        message=f"must-severity rule '{rule.id}' has no rationale",
        position=rule.position,
        suggestion=(
            'add `rationale = "..."` explaining why this rule is mandatory '
            "(what breaks if it is violated)"
        ),
        doc_url=K002_DOC_URL,
    )


def _check_must_without_examples(rule: Rule) -> Iterable[Diagnostic]:
    """K003 — a ``must`` rule lacks an example_good or example_bad.

    Examples cement understanding more reliably than prose for the LLM.
    INFO severity: this is a recommendation, not a defect.
    """
    if rule.severity != Severity.MUST:
        return
    has_good = rule.example_good is not None and rule.example_good.strip()
    has_bad = rule.example_bad is not None and rule.example_bad.strip()
    if has_good or has_bad:
        return
    yield Diagnostic(
        code=K003_CODE,
        severity=K003_SEVERITY,
        message=f"must-severity rule '{rule.id}' has no example_good or example_bad",
        position=rule.position,
        suggestion=(
            "add an `example_good` (canonical correct form) or "
            "`example_bad` (a typical violation) to make the rule concrete"
        ),
        doc_url=K003_DOC_URL,
    )
