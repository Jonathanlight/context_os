"""Ambiguity analyzers (category A) — vague directives, subjective wording.

Milestone 2.0 shipped A001. Milestone 2.1 fills the category with three
lexical rules built on the same pattern: a frozenset of unambiguous
trigger tokens, a normalized comparison against the rule title.

Codes ship as WARNING. An author can either fix them with a measurable
criterion or accept the noise — the analyzer never blocks compilation
on ambiguity.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# A001 — vague directive
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# A002 — subjective adjective
# ---------------------------------------------------------------------------

_SUBJECTIVE_ADJECTIVES = frozenset(
    {
        "clean",
        "good",
        "bad",
        "nice",
        "elegant",
        "proper",
        "appropriate",
        "suitable",
        "reasonable",
        "sensible",
        "smart",
        "stupid",
        "ugly",
        "beautiful",
        "tidy",
        "messy",
    }
)

A002_CODE = "A002"
A002_SEVERITY = DiagSeverity.WARNING
A002_DOC_URL = "https://contextos.dev/rules/A002"

# ---------------------------------------------------------------------------
# A003 — vague quantifier
# ---------------------------------------------------------------------------

_VAGUE_QUANTIFIERS = frozenset(
    {
        "usually",
        "often",
        "sometimes",
        "rarely",
        "frequently",
        "occasionally",
        "most",
        "few",
        "many",
        "several",
        "some",
        "a lot",
        "lots of",
        "plenty of",
    }
)

A003_CODE = "A003"
A003_SEVERITY = DiagSeverity.WARNING
A003_DOC_URL = "https://contextos.dev/rules/A003"

# ---------------------------------------------------------------------------
# A004 — hedging cadence
# ---------------------------------------------------------------------------

_HEDGING_PHRASES = frozenset(
    {
        "regularly",
        "as needed",
        "when appropriate",
        "if necessary",
        "if possible",
        "from time to time",
        "every now and then",
        "when in doubt",
        "where it makes sense",
        "where appropriate",
    }
)

A004_CODE = "A004"
A004_SEVERITY = DiagSeverity.WARNING
A004_DOC_URL = "https://contextos.dev/rules/A004"

# Token splitter: words are sequences of letters / digits / apostrophes.
# Punctuation is treated as a word boundary.
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every A* check against ``agent``."""
    _ = source  # reserved for future rules that need file-relative context
    for rule in agent.rules:
        yield from _check_vague_directive(rule)
        yield from _check_subjective_adjective(rule)
        yield from _check_vague_quantifier(rule)
        yield from _check_hedging_phrase(rule)


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


def _check_subjective_adjective(rule: Rule) -> Iterable[Diagnostic]:
    """A002 — flag a rule title that contains a subjective adjective."""
    tokens = {token.lower() for token in _WORD_RE.findall(rule.title)}
    offenders = sorted(tokens & _SUBJECTIVE_ADJECTIVES)
    if offenders:
        yield Diagnostic(
            code=A002_CODE,
            severity=A002_SEVERITY,
            message=(
                f"subjective adjective '{offenders[0]}' in: '{rule.title}'"
                if len(offenders) == 1
                else f"subjective adjectives {offenders} in: '{rule.title}'"
            ),
            position=rule.position,
            suggestion=(
                "replace the subjective term with a concrete criterion "
                "(e.g. 'clean' -> 'no function > 5 levels of nesting')"
            ),
            doc_url=A002_DOC_URL,
        )


def _check_vague_quantifier(rule: Rule) -> Iterable[Diagnostic]:
    """A003 — flag a rule title that hedges with a fuzzy quantifier."""
    normalized = " ".join(rule.title.lower().split())
    offender = _first_matching_phrase(normalized, _VAGUE_QUANTIFIERS)
    if offender is not None:
        yield Diagnostic(
            code=A003_CODE,
            severity=A003_SEVERITY,
            message=f"vague quantifier '{offender}' in: '{rule.title}'",
            position=rule.position,
            suggestion=(
                "give a measurable threshold (e.g. 'rarely' -> 'less than 1% of requests')"
            ),
            doc_url=A003_DOC_URL,
        )


def _check_hedging_phrase(rule: Rule) -> Iterable[Diagnostic]:
    """A004 — flag a rule that hedges cadence (regularly, as needed, ...)."""
    normalized = " ".join(rule.title.lower().split())
    offender = _first_matching_phrase(normalized, _HEDGING_PHRASES)
    if offender is not None:
        yield Diagnostic(
            code=A004_CODE,
            severity=A004_SEVERITY,
            message=f"hedging cadence '{offender}' in: '{rule.title}'",
            position=rule.position,
            suggestion=(
                "tie the cadence to a measurable trigger "
                "(e.g. 'regularly' -> 'on every PR' or 'when test coverage drops')"
            ),
            doc_url=A004_DOC_URL,
        )


def _first_matching_phrase(text: str, phrases: frozenset[str]) -> str | None:
    """Return the first phrase from ``phrases`` that appears as a whole-token
    span inside ``text`` (already lower-cased and whitespace-normalized).

    Whole-token semantics mean ``"rarely"`` matches in ``"fail rarely happens"``
    but not in ``"rarelyused"``. Multi-token phrases ("as needed") match as a
    contiguous substring with word boundaries on each side.
    """
    for phrase in phrases:
        pattern = rf"(^|\W){re.escape(phrase)}(\W|$)"
        if re.search(pattern, text):
            return phrase
    return None
