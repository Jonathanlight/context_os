"""GitHub Copilot target — ``.github/copilot-instructions.md``.

Copilot reads a single Markdown file at ``.github/copilot-instructions.md``
as the project's shared rule set. The format is flat-Markdown agent
context (same as codex/cline/windsurf), so the emitter delegates to
:func:`emit_flat_agent_markdown`.
"""

from __future__ import annotations

from contextos.ast.document import Document
from contextos.emitters._agent_base import emit_flat_agent_markdown


def emit_copilot_instructions(doc: Document) -> str:
    """Emit a Document as a GitHub Copilot instructions Markdown file."""
    return emit_flat_agent_markdown(doc)


__all__ = ["emit_copilot_instructions"]
