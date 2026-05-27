"""Cursor target emitter — ``.cursor/rules/*.mdc`` format.

The Cursor ``.mdc`` shape is different enough from CLAUDE.md / AGENTS.md
that it gets its own emitter rather than parameter-tweaks on the
Markdown one. Specifically:

- YAML frontmatter at the top (``description``, ``globs``, ``alwaysApply``).
- ALL-CAPS section names — no ``##`` Markdown headings.
- Dense bullet lists per section.

This is target-only for Milestone 3.2: no Cursor parser yet. Authors
who write their context in a ``.ctx`` can compile to Cursor; reading
an existing ``.mdc`` back into a Document is a follow-up.
"""

from __future__ import annotations

from contextos.ast.agent import Rule
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


def emit_cursor_mdc(doc: Document) -> str:
    """Emit a Document as a Cursor ``.mdc`` rules file.

    Output shape::

        ---
        description: Rules for {project}
        globs: ["**/*"]
        alwaysApply: true
        ---

        IDENTITY
        - <role>

        TECHNOLOGY STACK
        - python>=3.12

        ASSISTANT RULES
        - Must use type hints on public functions.
        - Should prefer composition over inheritance.

        CODING STYLE
        - 4 spaces, no tabs.

        FORBIDDEN PATTERNS
        - Wildcard imports.

        TOOLING
        - ruff
        - mypy

    Sections collapse silently when empty. Stack.forbidden,
    Stack.preferred, and Tools.forbidden have no representation in
    this format — they drop, same as the codex target.
    """
    parts: list[str] = []
    parts.extend(_emit_frontmatter(doc))

    agent = doc.agent
    if agent is not None:
        if agent.identity is not None:
            parts.extend(_emit_section_lines("IDENTITY", [agent.identity.role]))
        if agent.stack is not None and agent.stack.required:
            parts.extend(_emit_section("TECHNOLOGY STACK", agent.stack.required))
        if agent.rules:
            parts.extend(
                _emit_section(
                    "ASSISTANT RULES",
                    [_rule_to_bullet_text(rule) for rule in agent.rules],
                )
            )
        if agent.style is not None and agent.style.conventions:
            parts.extend(_emit_section("CODING STYLE", agent.style.conventions))
        if agent.forbidden_patterns:
            parts.extend(_emit_section("FORBIDDEN PATTERNS", agent.forbidden_patterns))
        if agent.tools is not None and agent.tools.required:
            parts.extend(_emit_section("TOOLING", agent.tools.required))

    return "\n".join(parts).rstrip() + "\n"


def _emit_frontmatter(doc: Document) -> list[str]:
    """Emit the YAML frontmatter that opens a ``.mdc`` file."""
    identity = doc.agent.identity if doc.agent is not None else None
    description = (
        f"Rules for {doc.project} — {identity.role}"
        if identity is not None and identity.role
        else f"Rules for {doc.project}"
    )
    return [
        "---",
        f"description: {description}",
        'globs: ["**/*"]',
        "alwaysApply: true",
        "---",
    ]


def _emit_section(heading: str, items: list[str]) -> list[str]:
    """ALL-CAPS heading + bullet list, blank-line separated from prior section."""
    parts = ["", heading]
    parts.extend(f"- {item}" for item in items)
    return parts


def _emit_section_lines(heading: str, lines: list[str]) -> list[str]:
    """ALL-CAPS heading + raw lines (no bullet prefix).

    Used for Identity, which carries a single paragraph rather than a list.
    """
    parts = ["", heading]
    parts.extend(lines)
    return parts


def _rule_to_bullet_text(rule: Rule) -> str:
    """Same severity-preservation logic as the Claude / Codex emitters."""
    title = rule.title.rstrip(".")
    leading = title.lower().split()[:1]
    leading_word = leading[0] if leading else ""
    if leading_word in _SEVERITY_LEADING_WORDS[rule.severity]:
        return f"{title}."
    prefix = _SEVERITY_PREFIX[rule.severity]
    return f"{prefix} {_lower_first(title)}."


def _lower_first(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]


__all__ = ["emit_cursor_mdc"]
