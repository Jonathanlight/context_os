"""Platform analyzers (category P) — target-aware authoring gotchas.

The P rules flag titles that leak machine-specific or author-specific
state into a context file meant to live in a repo. Three shipped in
Milestone 2.6:

- P001: a user's home directory baked into the rule (``/Users/alice/...``).
- P002: an email address in the title.
- P003: a bare HTTP/HTTPS URL in the title.

All three should live in structured fields (``links``, ``author``) or
prose, not inside a rule's operational text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# P001 — personal absolute path in title
# ---------------------------------------------------------------------------

P001_CODE = "P001"
P001_SEVERITY = DiagSeverity.WARNING
P001_DOC_URL = "https://contextos.dev/rules/P001"

# Matches a user-home pattern: /Users/foo, /home/foo, C:\Users\foo
# (with optional drive letter for the Windows case). The trailing
# segment ensures we don't match the literal "/Users" / "/home" alone.
_PERSONAL_PATH_RE = re.compile(
    r"(?:/Users/[A-Za-z0-9._-]+|"
    r"/home/[A-Za-z0-9._-]+|"
    r"[A-Z]:\\Users\\[A-Za-z0-9._-]+)",
)

# ---------------------------------------------------------------------------
# P002 — email address in title
# ---------------------------------------------------------------------------

P002_CODE = "P002"
P002_SEVERITY = DiagSeverity.WARNING
P002_DOC_URL = "https://contextos.dev/rules/P002"

# Conservative email regex — accepts the practical cases without trying to
# be RFC-5322-complete. Requires letter / digit on both sides of the @.
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)

# ---------------------------------------------------------------------------
# P003 — bare URL in title
# ---------------------------------------------------------------------------

P003_CODE = "P003"
P003_SEVERITY = DiagSeverity.WARNING
P003_DOC_URL = "https://contextos.dev/rules/P003"

_URL_RE = re.compile(r"https?://\S+")


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every P* check against ``agent``."""
    _ = source
    for rule in agent.rules:
        yield from _check_personal_path(rule)
        yield from _check_email(rule)
        yield from _check_bare_url(rule)


def _check_personal_path(rule: Rule) -> Iterable[Diagnostic]:
    """P001 — flag a title with a personal home directory path."""
    match = _PERSONAL_PATH_RE.search(rule.title)
    if match is None:
        return
    yield Diagnostic(
        code=P001_CODE,
        severity=P001_SEVERITY,
        message=(f"personal path '{match.group(0)}' in rule title: '{rule.title}'"),
        position=rule.position,
        suggestion=(
            "replace the absolute path with a project-relative path "
            "(e.g. `~/.config/myapp` or `./config`) or move the location "
            "to a `links` entry"
        ),
        doc_url=P001_DOC_URL,
    )


def _check_email(rule: Rule) -> Iterable[Diagnostic]:
    """P002 — flag a title containing an email address."""
    match = _EMAIL_RE.search(rule.title)
    if match is None:
        return
    yield Diagnostic(
        code=P002_CODE,
        severity=P002_SEVERITY,
        message=(f"email address '{match.group(0)}' in rule title: '{rule.title}'"),
        position=rule.position,
        suggestion=(
            "move contact details to the document's `author` field or to a "
            "`links` entry; rule titles should describe behaviour, not people"
        ),
        doc_url=P002_DOC_URL,
    )


def _check_bare_url(rule: Rule) -> Iterable[Diagnostic]:
    """P003 — flag a title containing a bare URL."""
    match = _URL_RE.search(rule.title)
    if match is None:
        return
    yield Diagnostic(
        code=P003_CODE,
        severity=P003_SEVERITY,
        message=f"bare URL '{match.group(0)}' in rule title: '{rule.title}'",
        position=rule.position,
        suggestion=(
            "move the URL to the rule's `links` field; the title should "
            "describe the directive, the link supports it"
        ),
        doc_url=P003_DOC_URL,
    )
