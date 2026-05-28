"""Emitters: AST → target-specific output formats.

Milestone 1.5 shipped :func:`emit_claude_markdown` for the
``claude_code`` target. Phase 3 added the five remaining agent
targets — codex (AGENTS.md), cursor (.cursor/rules/*.mdc),
copilot (.github/copilot-instructions.md), cline (.clinerules), and
windsurf (.windsurfrules). Phase 5 adds the Anthropic Skills
emitter; Phase 6 adds the RAG corpus manifest emitter.
"""

from __future__ import annotations

from contextos.emitters.claude import emit_claude_markdown
from contextos.emitters.cline import emit_clinerules
from contextos.emitters.codex import emit_codex_markdown
from contextos.emitters.copilot import emit_copilot_instructions
from contextos.emitters.cursor import emit_cursor_mdc
from contextos.emitters.windsurf import emit_windsurfrules

__all__ = [
    "emit_claude_markdown",
    "emit_clinerules",
    "emit_codex_markdown",
    "emit_copilot_instructions",
    "emit_cursor_mdc",
    "emit_windsurfrules",
]
