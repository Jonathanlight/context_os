"""Shared flat-Markdown emit logic for agent-context targets.

Several agent targets produce the same shape: H1 project header,
``## Section`` headings, flat bullet lists under each section (no H3
sub-sections), and the Must/Should/May severity prefixing convention.
The codex (AGENTS.md), Copilot (.github/copilot-instructions.md), Cline
(.clinerules), and Windsurf (.windsurfrules) targets share this layout.

The claude_code target uses H3 sub-sections under Stack/Tools and lives
in its own module (``claude.py``).

This module is private (leading ``_``). Public emitters import
``emit_flat_agent_markdown`` and expose their own named function for the
CLI dispatch table.
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


def emit_flat_agent_markdown(doc: Document) -> str:
    """Emit a Document as flat-Markdown agent context.

    Output shape::

        # <project>

        ## Identity

        <role>

        ## Stack

        - python>=3.12

        ## Rules

        - Must use type hints.
        - Should sanitize input.

        ## Style

        - 4 spaces

        ## Forbidden patterns

        - wildcard imports

        ## Tools

        - ruff

    Trailing newline, no per-line trailing whitespace, deterministic
    section order. Empty sub-buckets collapse silently (drops
    Stack.forbidden / Stack.preferred / Tools.forbidden which the flat
    layout cannot represent).
    """
    parts: list[str] = []
    parts.append(f"# {doc.project}")

    agent = doc.agent
    if agent is None:
        return "\n".join(parts).rstrip() + "\n"

    if agent.identity is not None:
        parts.extend(["", "## Identity", "", agent.identity.role])

    if agent.stack is not None and agent.stack.required:
        parts.extend(["", "## Stack", ""])
        parts.extend(f"- {item}" for item in agent.stack.required)

    if agent.rules:
        parts.extend(["", "## Rules", ""])
        for rule in agent.rules:
            parts.append(f"- {_rule_to_bullet_text(rule)}")

    if agent.style is not None and agent.style.conventions:
        parts.extend(["", "## Style", ""])
        parts.extend(f"- {item}" for item in agent.style.conventions)

    if agent.forbidden_patterns:
        parts.extend(["", "## Forbidden patterns", ""])
        parts.extend(f"- {item}" for item in agent.forbidden_patterns)

    if agent.tools is not None and agent.tools.required:
        parts.extend(["", "## Tools", ""])
        parts.extend(f"- {item}" for item in agent.tools.required)

    return "\n".join(parts).rstrip() + "\n"


def _rule_to_bullet_text(rule: Rule) -> str:
    """Format a rule as bullet text, preserving severity through wording."""
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


__all__ = ["emit_flat_agent_markdown"]
