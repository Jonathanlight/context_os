"""LLM-friendliness analyzers (category F) — formatting that hurts the model.

These are not content errors. They are shape errors: things the LLM has
to fight through even when the underlying directive is fine. Excessive
ALL CAPS dilutes attention. Long titles break the bullet-list signal.
Duplicates waste context tokens and create disagreement risk.

All F rules ship as ``WARNING``; the author may dismiss them but the
suggestion is always a concrete formatting fix.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# F001 — excessive ALL CAPS
# ---------------------------------------------------------------------------

F001_CODE = "F001"
F001_SEVERITY = DiagSeverity.WARNING
F001_DOC_URL = "https://contextos.dev/rules/F001"

# Trigger only on long-ish titles so "USE HTTPS" (8 letters) doesn't false-fire.
_F001_MIN_LETTERS = 15
_F001_CAPS_RATIO = 0.70

# ---------------------------------------------------------------------------
# F002 — rule title too long
# ---------------------------------------------------------------------------

F002_CODE = "F002"
F002_SEVERITY = DiagSeverity.WARNING
F002_DOC_URL = "https://contextos.dev/rules/F002"

_F002_MAX_CHARS = 120

# ---------------------------------------------------------------------------
# F003 — duplicate rule
# ---------------------------------------------------------------------------

F003_CODE = "F003"
F003_SEVERITY = DiagSeverity.WARNING
F003_DOC_URL = "https://contextos.dev/rules/F003"

# Whitespace + punctuation stripped, lowercased — see _normalize_title.
_PUNCT_STRIP_RE = re.compile(r"[^\w\s]")


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every F* check against ``agent``."""
    _ = source
    for rule in agent.rules:
        yield from _check_excessive_caps(rule)
        yield from _check_title_too_long(rule)
    yield from _check_duplicate_rules(agent)


def _check_excessive_caps(rule: Rule) -> Iterable[Diagnostic]:
    """F001 — flag a rule title that is mostly uppercase."""
    letters = [c for c in rule.title if c.isalpha()]
    if len(letters) < _F001_MIN_LETTERS:
        return
    uppercase = sum(1 for c in letters if c.isupper())
    ratio = uppercase / len(letters)
    if ratio >= _F001_CAPS_RATIO:
        yield Diagnostic(
            code=F001_CODE,
            severity=F001_SEVERITY,
            message=(
                f"excessive ALL CAPS in rule title "
                f"({uppercase}/{len(letters)} letters uppercase): '{rule.title}'"
            ),
            position=rule.position,
            suggestion=(
                "use sentence case for the title; reserve ALL CAPS for "
                "well-known acronyms only (HTTPS, JSON, ...)"
            ),
            doc_url=F001_DOC_URL,
        )


def _check_title_too_long(rule: Rule) -> Iterable[Diagnostic]:
    """F002 — flag a rule title that exceeds the readability ceiling."""
    if len(rule.title) > _F002_MAX_CHARS:
        yield Diagnostic(
            code=F002_CODE,
            severity=F002_SEVERITY,
            message=(f"rule title is {len(rule.title)} characters long (limit: {_F002_MAX_CHARS})"),
            position=rule.position,
            suggestion=(
                "split the title into two rules, or move the elaboration "
                "into the 'rationale' or 'detail' field"
            ),
            doc_url=F002_DOC_URL,
        )


def _check_duplicate_rules(agent: AgentDocument) -> Iterable[Diagnostic]:
    """F003 — flag rules whose normalized titles collide.

    Compares lowercase + punctuation-stripped + whitespace-collapsed titles.
    The first occurrence of each title is treated as canonical; every
    later duplicate emits a diagnostic referencing the canonical's id.
    """
    seen: dict[str, Rule] = {}
    for rule in agent.rules:
        normalized = _normalize_title(rule.title)
        if not normalized:
            continue
        canonical = seen.get(normalized)
        if canonical is None:
            seen[normalized] = rule
            continue
        yield Diagnostic(
            code=F003_CODE,
            severity=F003_SEVERITY,
            message=(
                f"duplicate of rule '{canonical.id}': '{rule.title}' (normalized to '{normalized}')"
            ),
            position=rule.position,
            suggestion=(
                f"delete this rule or merge its content into '{canonical.id}'; "
                "duplicates waste context tokens and risk silent disagreement"
            ),
            doc_url=F003_DOC_URL,
        )


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(_PUNCT_STRIP_RE.sub(" ", title).lower().split())
