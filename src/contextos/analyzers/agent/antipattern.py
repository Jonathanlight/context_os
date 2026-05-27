"""Anti-pattern analyzers (category X) — known-bad shapes for rules.

X rules flag titles that look like authoring mistakes: placeholders
left behind from a template (TODO, ``<INSERT_NAME>``), or directives
phrased as questions. All WARNING — the analyzer treats them as
likely bugs the author wants to know about, not as fatal errors.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# X001 — placeholder marker (TODO / FIXME / XXX / HACK)
# ---------------------------------------------------------------------------

X001_CODE = "X001"
X001_SEVERITY = DiagSeverity.WARNING
X001_DOC_URL = "https://contextos.dev/rules/X001"

# Whole-token, case-insensitive. Match `TODO`, `Todo:`, `(todo)` etc., but
# NOT `TODO-list` or `FIXMEs`. Hyphens count as part of the surrounding
# token so the rule doesn't fire on compound words like `TODO-list`.
_PLACEHOLDER_MARKERS_RE = re.compile(
    r"(?<![A-Za-z\-])(TODO|FIXME|XXX|HACK)(?![A-Za-z\-])", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# X002 — unfilled template placeholder
# ---------------------------------------------------------------------------

X002_CODE = "X002"
X002_SEVERITY = DiagSeverity.WARNING
X002_DOC_URL = "https://contextos.dev/rules/X002"

# Three placeholder shapes we routinely see in starter templates:
# - <INSERT_NAME>, <YOUR_PROJECT>  (angle brackets + ALL_CAPS_SNAKE_CASE)
# - {your_project_name}             (curly braces + snake/dash word)
# - [INSERT FOO HERE]               (square brackets containing "INSERT")
_TEMPLATE_PLACEHOLDER_RE = re.compile(
    r"<[A-Z_][A-Z0-9_]*>|"
    r"\{[a-zA-Z_][a-zA-Z0-9_\-]*\}|"
    r"\[INSERT[^\]]*\]",
)

# ---------------------------------------------------------------------------
# X003 — directive phrased as a question
# ---------------------------------------------------------------------------

X003_CODE = "X003"
X003_SEVERITY = DiagSeverity.WARNING
X003_DOC_URL = "https://contextos.dev/rules/X003"


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every X* check against ``agent``."""
    _ = source
    for rule in agent.rules:
        yield from _check_placeholder_marker(rule)
        yield from _check_unfilled_template(rule)
        yield from _check_question_directive(rule)


def _check_placeholder_marker(rule: Rule) -> Iterable[Diagnostic]:
    """X001 — flag a title carrying a TODO/FIXME-style marker."""
    match = _PLACEHOLDER_MARKERS_RE.search(rule.title)
    if match is None:
        return
    marker = match.group(1).upper()
    yield Diagnostic(
        code=X001_CODE,
        severity=X001_SEVERITY,
        message=(f"rule title contains placeholder marker '{marker}': '{rule.title}'"),
        position=rule.position,
        suggestion=(
            f"finish the rule and remove the {marker} marker, "
            "or delete the rule if it was never needed"
        ),
        doc_url=X001_DOC_URL,
    )


def _check_unfilled_template(rule: Rule) -> Iterable[Diagnostic]:
    """X002 — flag a title with an unfilled template placeholder."""
    match = _TEMPLATE_PLACEHOLDER_RE.search(rule.title)
    if match is None:
        return
    placeholder = match.group(0)
    yield Diagnostic(
        code=X002_CODE,
        severity=X002_SEVERITY,
        message=(
            f"rule title contains unfilled template placeholder '{placeholder}': '{rule.title}'"
        ),
        position=rule.position,
        suggestion=(
            f"replace {placeholder} with the actual value, "
            "or delete the rule if it was never customized"
        ),
        doc_url=X002_DOC_URL,
    )


def _check_question_directive(rule: Rule) -> Iterable[Diagnostic]:
    """X003 — flag a title that is a question rather than a directive."""
    if rule.title.rstrip().endswith("?"):
        yield Diagnostic(
            code=X003_CODE,
            severity=X003_SEVERITY,
            message=f"rule title is a question, not a directive: '{rule.title}'",
            position=rule.position,
            suggestion=(
                "rewrite as an imperative ('Validate inputs' instead of "
                "'Should we validate inputs?')"
            ),
            doc_url=X003_DOC_URL,
        )
