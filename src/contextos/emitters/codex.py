"""``AGENTS.md`` emitter — :class:`Document` → Markdown for the codex target.

Same byte-stability contract as the Claude emitter; the structural
difference is that AGENTS.md uses flat bullet lists under Stack / Tools
instead of H3 sub-sections. A document that round-trips cleanly through
the claude_code target will also round-trip through codex with the
exact same fields preserved (project / identity / stack-required /
style / tools-required / forbidden_patterns / rule severities).

Lossy fields are identical to the claude emitter:
Rule.id, rationale, detail, examples, tags, links, position, applies_to.
Document.ctx_version, languages, authors, version.
AgentDocument.prose.

Codex-specific quirks today:
- Flat bullet list under Stack: only the ``required`` bucket is emitted.
  ``stack.forbidden`` and ``stack.preferred`` cannot survive a codex
  round-trip; if those buckets carry content, the emitter still drops
  them silently. Authors who need the forbidden / preferred buckets
  should target ``claude_code`` instead.
- Same flat-list rule for Tools: only ``tools.required`` is emitted.
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


def emit_codex_markdown(doc: Document) -> str:
    """Emit a Document as an AGENTS.md-style Markdown string.

    Trailing newline, no per-line trailing whitespace. Same severity-
    preservation strategy as the Claude emitter: prefix Must / Should /
    May when the rule title doesn't already imply its severity.
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
    """Emit ``## Stack`` as a flat bullet list (codex convention).

    Only the ``required`` bucket survives — forbidden and preferred have
    no representation in AGENTS.md's flat layout. The emitter silently
    drops them; ``ctx lint`` could one day flag this as a target-specific
    information loss (Phase 3+ enhancement).
    """
    if not stack.required:
        return []
    parts: list[str] = ["", "## Stack", ""]
    parts.extend(f"- {item}" for item in stack.required)
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
    """Emit ``## Tools`` as a flat bullet list — same shape as Stack."""
    if not tools.required:
        return []
    parts: list[str] = ["", "## Tools", ""]
    parts.extend(f"- {item}" for item in tools.required)
    return parts


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
