"""Description-quality skill analyzers — S001, S002, S003."""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.skill import DESCRIPTION_MAX_CHARS, SkillDocument
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# S001 — description missing trigger phrasing
# ---------------------------------------------------------------------------

S001_CODE = "S001"
S001_SEVERITY = DiagSeverity.WARNING
S001_DOC_URL = "https://contextos.dev/rules/S001"

_TRIGGER_PHRASES = (
    "when ",
    "triggers ",
    "trigger ",
    "use this ",
    "use when",
    "invoke when",
    "asks to ",
    "asks for ",
    "user requests",
    "user wants",
    "user needs",
)
"""Lowercase phrases that indicate the description carries trigger guidance.

The model needs to know **when** to invoke the skill, not just what it
does. Descriptions like "Extracts text from PDFs" describe behavior but
don't tell the router to fire on a PDF-related user prompt; descriptions
like "Triggers when the user uploads a PDF..." do.
"""

# ---------------------------------------------------------------------------
# S002 — description too short
# ---------------------------------------------------------------------------

S002_CODE = "S002"
S002_SEVERITY = DiagSeverity.WARNING
S002_DOC_URL = "https://contextos.dev/rules/S002"

S002_MIN_CHARS = 50
"""Floor below which a description is too thin to carry a clean trigger.

Empirically, descriptions under ~50 characters rarely have room for
both "what the skill does" and "when to use it" — they collapse into
one or the other, and the trigger signal suffers.
"""

# ---------------------------------------------------------------------------
# S003 — description close to the hard cap
# ---------------------------------------------------------------------------

S003_CODE = "S003"
S003_SEVERITY = DiagSeverity.INFO
S003_DOC_URL = "https://contextos.dev/rules/S003"

S003_SOFT_CAP_CHARS = 800
"""Soft cap. The hard cap is :data:`DESCRIPTION_MAX_CHARS` (1024); past
this soft warning, the description starts eating the rest of the context
budget every time the skill is registered.
"""


def check(skill: SkillDocument) -> Iterable[Diagnostic]:
    """Run every description-quality check against ``skill``."""
    yield from _check_missing_trigger(skill)
    yield from _check_too_short(skill)
    yield from _check_too_long(skill)


def _check_missing_trigger(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S001 — description lacks any trigger phrasing.

    Checked against a lowercase folded version of the description so the
    phrase matches regardless of capitalization. The phrase list is
    deliberately conservative — false positives on this rule are loud
    (it's WARNING) so we err toward only firing when no trigger word
    appears at all.
    """
    body = _normalize(skill.description)
    if any(phrase in body for phrase in _TRIGGER_PHRASES):
        return
    yield Diagnostic(
        code=S001_CODE,
        severity=S001_SEVERITY,
        message=(
            f"skill '{skill.name}' description has no trigger phrasing "
            "(e.g. 'triggers when…', 'use this when…', 'asks to…')"
        ),
        suggestion=(
            "describe WHEN the model should invoke this skill — e.g. "
            "'Triggers when the user asks to extract text from a PDF.'"
        ),
        doc_url=S001_DOC_URL,
    )


def _check_too_short(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S002 — description below :data:`S002_MIN_CHARS` (excluding whitespace).

    Length is measured on the visible content; collapsing multiple
    whitespace runs into single spaces prevents a description like
    "      Short.        " from clearing the floor on padding alone.
    """
    visible = re.sub(r"\s+", " ", skill.description.strip())
    if len(visible) >= S002_MIN_CHARS:
        return
    yield Diagnostic(
        code=S002_CODE,
        severity=S002_SEVERITY,
        message=(
            f"skill '{skill.name}' description is {len(visible)} chars "
            f"(minimum {S002_MIN_CHARS}) — too short to carry a usable "
            "trigger signal"
        ),
        suggestion=(
            "expand to one or two sentences: the first describes the "
            "capability, the second names the trigger condition"
        ),
        doc_url=S002_DOC_URL,
    )


def _check_too_long(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S003 — description over the soft cap but under the hard cap.

    Past :data:`S003_SOFT_CAP_CHARS` characters, the description starts
    crowding the context window. The hard cap is enforced by the AST
    (:data:`DESCRIPTION_MAX_CHARS`); this rule warns before we hit it.
    """
    length = len(skill.description)
    if length <= S003_SOFT_CAP_CHARS:
        return
    yield Diagnostic(
        code=S003_CODE,
        severity=S003_SEVERITY,
        message=(
            f"skill '{skill.name}' description is {length} chars "
            f"(soft cap {S003_SOFT_CAP_CHARS}, hard cap "
            f"{DESCRIPTION_MAX_CHARS}) — consider moving detail into "
            "the body"
        ),
        suggestion=(
            "the description is loaded into every skill-registration "
            "prompt; keep it scannable and move usage notes / examples "
            "into the Markdown body"
        ),
        doc_url=S003_DOC_URL,
    )


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace for trigger-phrase matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()
