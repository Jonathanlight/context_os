"""Contradiction analyzers (category C) — rules that disagree.

Milestone 2.5 ships C001 only: a lexical antonym-overlap heuristic. The
master spec (``.claude/ALGORITHMS.md`` §6) estimates this approach at
~80 % precision and ~50 % recall — enough to catch the obvious cases
without an NLI model. NLI-based detection lands post-MVP.

Algorithm

1. For each pair of rules ``(r_i, r_j)``, tokenize both titles.
2. If any antonym pair from :data:`_ANTONYM_PAIRS` spans the two token
   sets (one word in ``r_i``, its opposite in ``r_j``), continue.
3. Compute "subject overlap": the intersection of the two token sets
   after removing stopwords and the antonym words themselves.
4. If the overlap is non-empty, emit C001 with both rule IDs.

The empty-overlap guard is what makes the heuristic specific: ``Always
validate inputs`` and ``Never share keys`` both contain an antonym
pair, but they're about different subjects, so they don't fire.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from itertools import combinations

from contextos.ast.agent import AgentDocument, Rule
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# C001 — antonym-pair contradiction
# ---------------------------------------------------------------------------

C001_CODE = "C001"
C001_SEVERITY = DiagSeverity.WARNING
C001_DOC_URL = "https://contextos.dev/rules/C001"

# Single-token antonym pairs only — multi-word forms like "must not" survive
# tokenization as two tokens and would need a separate matcher (deferred).
_ANTONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("always", "never"),
    ("required", "forbidden"),
    ("allowed", "prohibited"),
    ("allow", "forbid"),
    ("enable", "disable"),
    ("include", "exclude"),
    ("public", "private"),
    ("mutable", "immutable"),
    ("synchronous", "asynchronous"),
    ("sync", "async"),
    ("encrypted", "plaintext"),
    ("local", "remote"),
    ("explicit", "implicit"),
    ("before", "after"),
)

# Lightweight English stopword set — kept small to stay deterministic; richer
# sets bring locale + grammatical baggage we don't need for this heuristic.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "on",
        "in",
        "to",
        "for",
        "with",
        "and",
        "or",
        "is",
        "are",
        "be",
        "been",
        "by",
        "as",
        "at",
        "from",
        "all",
        "any",
        "it",
        "its",
        "this",
        "that",
        "use",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]+")


def check(agent: AgentDocument, source: str | None = None) -> Iterable[Diagnostic]:
    """Run every C* check against ``agent``."""
    _ = source
    for rule_a, rule_b in combinations(agent.rules, 2):
        yield from _check_pair(rule_a, rule_b)


def _check_pair(rule_a: Rule, rule_b: Rule) -> Iterable[Diagnostic]:
    """C001 — flag two rules that share a subject but use antonym words."""
    tokens_a = _tokenize(rule_a.title)
    tokens_b = _tokenize(rule_b.title)
    antonym = _find_antonym_pair(tokens_a, tokens_b)
    if antonym is None:
        return
    word_a, word_b = antonym

    subject_a = (tokens_a - {word_a}) - _STOPWORDS
    subject_b = (tokens_b - {word_b}) - _STOPWORDS
    shared = subject_a & subject_b
    if not shared:
        return

    yield Diagnostic(
        code=C001_CODE,
        severity=C001_SEVERITY,
        message=(
            f"contradiction: rule '{rule_a.id}' uses '{word_a}' while "
            f"rule '{rule_b.id}' uses '{word_b}' "
            f"(shared subject: {sorted(shared)})"
        ),
        position=rule_b.position,
        suggestion=(
            "resolve the contradiction: keep the directive that applies "
            "and delete or rewrite the other rule, or qualify each rule "
            "with an `applies_to` to make the scopes disjoint"
        ),
        doc_url=C001_DOC_URL,
    )


def _tokenize(text: str) -> set[str]:
    """Lowercased alphabetic tokens — punctuation and digits dropped."""
    return {token.lower() for token in _WORD_RE.findall(text)}


def _find_antonym_pair(tokens_a: set[str], tokens_b: set[str]) -> tuple[str, str] | None:
    """Return ``(word_in_a, word_in_b)`` if any antonym pair spans the sets.

    The returned tuple always reflects which side carried which word, so the
    diagnostic message lines up with ``rule_a`` and ``rule_b`` in the caller.
    """
    for word_x, word_y in _ANTONYM_PAIRS:
        if word_x in tokens_a and word_y in tokens_b:
            return (word_x, word_y)
        if word_y in tokens_a and word_x in tokens_b:
            return (word_y, word_x)
    return None
