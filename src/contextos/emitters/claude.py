"""``CLAUDE.md`` emitter — :class:`Document` → Markdown, byte-stable.

Same input ``Document`` always produces the same Markdown string, byte for
byte. That's the explicit contract of Milestone 1.5 and the precondition
for the round-trip property test in 1.6.

Symmetric with the ``claude_code`` Markdown parser
(:mod:`contextos.parsers.markdown_parser`): emit follows the same section
order and alias names the parser recognizes, so a ``parse → emit → parse``
cycle preserves the semantic content.

Intentionally lossy
-------------------

The bullet-rule format observed in real ``CLAUDE.md`` files only carries
the rule title. Several :class:`Rule` fields therefore do not survive
emit:

- ``id`` — the parser will regenerate ``MD-001`` etc. on the next read
- ``rationale``, ``detail``, ``example_good``, ``example_bad``
- ``tags``, ``links``, ``position``, ``applies_to``

To preserve severity across a round-trip, the emitter prefixes the title
with the severity-implying verb (``Must``, ``Should``, ``May``) when the
title's leading words do not already imply that severity.

Document-level fields not emitted: ``ctx_version``, ``languages``,
``authors``, ``version``. ``AgentDocument.prose`` is also not emitted —
Milestone 1.5 ships the structural shape only.

Future targets that need rich, lossless emission can subclass this module
or live alongside under :mod:`contextos.emitters` — the public API is the
function, not a class, so adding a class wrapper later is non-breaking.
"""

from __future__ import annotations

from contextos.ast.agent import (
    Identity,
    Rule,
    Stack,
    Style,
    Tools,
)
from contextos.ast.common import Severity
from contextos.ast.document import Document

_SEVERITY_PREFIX: dict[Severity, str] = {
    Severity.MUST: "Must",
    Severity.SHOULD: "Should",
    Severity.MAY: "May",
}

_SEVERITY_LEADING_WORDS: dict[Severity, frozenset[str]] = {
    Severity.MUST: frozenset({"must", "never", "always", "don't", "do"}),
    Severity.SHOULD: frozenset({"should", "prefer", "avoid", "recommended"}),
    Severity.MAY: frozenset({"may", "can", "could", "consider", "optional"}),
}


def emit_claude_markdown(doc: Document) -> str:
    """Emit a Document as a CLAUDE.md-style Markdown string.

    The output ends with a single trailing newline and contains no trailing
    whitespace on any line, so it diffs cleanly under default git settings.
    """
    parts: list[str] = []
    parts.append(f"# {doc.project}")

    agent = doc.agent
    if agent is not None:
        if agent.identity is not None:
            parts.extend(_emit_identity(agent.identity))
        if agent.stack is not None:
            parts.extend(_emit_stack(agent.stack))
        if agent.rules:
            parts.extend(_emit_rules(agent.rules))
        if agent.style is not None:
            parts.extend(_emit_style(agent.style))
        if agent.forbidden_patterns:
            parts.extend(_emit_forbidden_patterns(agent.forbidden_patterns))
        if agent.tools is not None:
            parts.extend(_emit_tools(agent.tools))

    return "\n".join(parts).rstrip() + "\n"


def _emit_identity(identity: Identity) -> list[str]:
    return ["", "## Identity", "", identity.role]


def _emit_stack(stack: Stack) -> list[str]:
    """Emit ``## Stack`` only when at least one bucket is populated.

    A Stack with three empty lists collapses to nothing — otherwise emit
    would produce a bare ``## Stack`` heading that the parser drops on the
    next read, breaking the idempotence property.
    """
    if not (stack.required or stack.forbidden or stack.preferred):
        return []
    parts: list[str] = ["", "## Stack"]
    parts.extend(_emit_h3_bullets("Required", stack.required))
    parts.extend(_emit_h3_bullets("Forbidden", stack.forbidden))
    parts.extend(_emit_h3_bullets("Preferred", stack.preferred))
    return parts


def _emit_rules(rules: list[Rule]) -> list[str]:
    parts: list[str] = ["", "## Rules", ""]
    for rule in rules:
        parts.append(f"- {_rule_to_bullet_text(rule)}")
    return parts


def _emit_style(style: Style) -> list[str]:
    if not style.conventions:
        return []
    parts: list[str] = ["", "## Style", ""]
    parts.extend(f"- {item}" for item in style.conventions)
    return parts


def _emit_forbidden_patterns(patterns: list[str]) -> list[str]:
    parts: list[str] = ["", "## Forbidden patterns", ""]
    parts.extend(f"- {item}" for item in patterns)
    return parts


def _emit_tools(tools: Tools) -> list[str]:
    """Emit ``## Tools`` only when at least one bucket is populated."""
    if not (tools.required or tools.forbidden):
        return []
    parts: list[str] = ["", "## Tools"]
    parts.extend(_emit_h3_bullets("Required", tools.required))
    parts.extend(_emit_h3_bullets("Forbidden", tools.forbidden))
    return parts


def _emit_h3_bullets(heading: str, items: list[str]) -> list[str]:
    """Emit an H3 sub-section + bullet list, or nothing for an empty list."""
    if not items:
        return []
    parts = ["", f"### {heading}", ""]
    parts.extend(f"- {item}" for item in items)
    return parts


def _rule_to_bullet_text(rule: Rule) -> str:
    """Format a rule as bullet text, preserving severity through wording.

    When the title's first word already implies the rule's severity (per
    :data:`_SEVERITY_LEADING_WORDS`), the title is emitted as-is. Otherwise
    the title is prefixed with ``Must``/``Should``/``May`` so the parser's
    lexical severity inference recovers the right value on the next read.
    """
    title = rule.title.rstrip(".")
    leading = title.lower().split()[:1]
    leading_word = leading[0] if leading else ""
    if leading_word in _SEVERITY_LEADING_WORDS[rule.severity]:
        return f"{title}."
    prefix = _SEVERITY_PREFIX[rule.severity]
    return f"{prefix} {_lower_first(title)}."


def _lower_first(text: str) -> str:
    """Lowercase the first character; leave the rest untouched."""
    if not text:
        return text
    return text[0].lower() + text[1:]
