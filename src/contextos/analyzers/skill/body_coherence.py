"""Body/metadata coherence skill analyzers — S004, S005, S006."""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.skill import SkillDocument
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# S004 — missing example_invocation
# ---------------------------------------------------------------------------

S004_CODE = "S004"
S004_SEVERITY = DiagSeverity.INFO
S004_DOC_URL = "https://contextos.dev/rules/S004"

# ---------------------------------------------------------------------------
# S005 — H1 in body absent or mismatched with title
# ---------------------------------------------------------------------------

S005_CODE = "S005"
S005_SEVERITY = DiagSeverity.INFO
S005_DOC_URL = "https://contextos.dev/rules/S005"

_H1_PATTERN = re.compile(r"^\s*#\s+(?P<text>.+?)\s*$", re.MULTILINE)
"""Match an atx-style H1 anywhere in the body, capturing its text."""

# ---------------------------------------------------------------------------
# S006 — trigger_keywords appear verbatim in description
# ---------------------------------------------------------------------------

S006_CODE = "S006"
S006_SEVERITY = DiagSeverity.INFO
S006_DOC_URL = "https://contextos.dev/rules/S006"


def check(skill: SkillDocument) -> Iterable[Diagnostic]:
    """Run every coherence check against ``skill``."""
    yield from _check_example_invocation(skill)
    yield from _check_body_h1(skill)
    yield from _check_keyword_overlap(skill)


def _check_example_invocation(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S004 — recommend an ``example_invocation`` when missing.

    The example_invocation is the literal user-prompt shape the skill
    expects to handle. It pins down the trigger far more concretely
    than prose can; skills without one routinely misfire on edge cases.
    """
    if skill.example_invocation and skill.example_invocation.strip():
        return
    yield Diagnostic(
        code=S004_CODE,
        severity=S004_SEVERITY,
        message=(
            f"skill '{skill.name}' has no `example_invocation` — the "
            "model has no concrete sample of when to fire"
        ),
        suggestion=(
            'add `example_invocation = "..."` with a verbatim user '
            "prompt that should trigger this skill"
        ),
        doc_url=S004_DOC_URL,
    )


def _check_body_h1(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S005 — body should open with an H1 matching the title.

    The first H1 anchors the body as the skill's documentation. Real
    Anthropic SKILL.md files almost universally lead with ``# <title>``
    and the model uses that H1 to confirm the right document was
    loaded. A body with no H1, or an H1 whose text doesn't match the
    YAML title, signals drift between the metadata and the prose.
    """
    if not skill.body.strip():
        # Body-less skill — that's a structure problem, not a heading one.
        return
    match = _H1_PATTERN.search(skill.body)
    if match is None:
        yield Diagnostic(
            code=S005_CODE,
            severity=S005_SEVERITY,
            message=(
                f"skill '{skill.name}' body has no H1 — add `# "
                f"{skill.title}` at the top of the body"
            ),
            suggestion=(
                "open the body with an H1 matching the YAML title so "
                "the model can confirm the loaded document"
            ),
            doc_url=S005_DOC_URL,
        )
        return
    h1_text = match.group("text").strip()
    if not _titles_match(h1_text, skill.title):
        yield Diagnostic(
            code=S005_CODE,
            severity=S005_SEVERITY,
            message=(
                f"skill '{skill.name}' body H1 '{h1_text}' does not "
                f"match YAML title '{skill.title}'"
            ),
            suggestion=(
                "align the body H1 with the YAML `title` field so the "
                "skill identifies itself consistently"
            ),
            doc_url=S005_DOC_URL,
        )


def _titles_match(h1: str, title: str) -> bool:
    """Case-insensitive comparison with whitespace + bold-marker tolerance."""
    return _normalize_title(h1) == _normalize_title(title)


def _normalize_title(text: str) -> str:
    """Lowercase + strip bold/italic markers + collapse whitespace."""
    cleaned = re.sub(r"[*_`]+", "", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _check_keyword_overlap(skill: SkillDocument) -> Iterable[Diagnostic]:
    """S006 — every ``trigger_keyword`` already present verbatim in the description.

    When the description already mentions every trigger keyword, the
    ``trigger_keywords`` field is redundant — the keyword router would
    fire on the description's tokens anyway. The list still costs YAML
    bytes and screen real-estate; flag it so the author can either
    remove it or expand the keyword set with terms the description
    didn't already cover.
    """
    if not skill.trigger_keywords:
        return
    description_lower = skill.description.lower()
    covered = [kw for kw in skill.trigger_keywords if kw.lower() in description_lower]
    if len(covered) != len(skill.trigger_keywords):
        return
    yield Diagnostic(
        code=S006_CODE,
        severity=S006_SEVERITY,
        message=(
            f"skill '{skill.name}' trigger_keywords {sorted(covered)} "
            "are already present verbatim in the description — the "
            "field adds no signal"
        ),
        suggestion=(
            "either remove the redundant `trigger_keywords` field, or "
            "extend it with synonyms the description doesn't cover"
        ),
        doc_url=S006_DOC_URL,
    )
