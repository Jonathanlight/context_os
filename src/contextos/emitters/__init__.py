"""Emitters: AST → target-specific output formats.

Milestone 1.5 ships :func:`emit_claude_markdown` for the ``claude_code``
target. Phase 3 adds codex (AGENTS.md), cursor, copilot, cline, windsurf.
Phase 5 adds the Anthropic Skills emitter; Phase 6 adds the RAG corpus
manifest emitter.
"""

from __future__ import annotations

from contextos.emitters.claude import emit_claude_markdown
from contextos.emitters.cursor import emit_cursor_mdc

__all__ = ["emit_claude_markdown", "emit_cursor_mdc"]
