"""Cline target — ``.clinerules``.

Cline reads ``.clinerules`` at the repo root as the project's persistent
rule set. Same flat-Markdown shape as codex/copilot/windsurf, delegated
to :func:`emit_flat_agent_markdown`.
"""

from __future__ import annotations

from contextos.ast.document import Document
from contextos.emitters._agent_base import emit_flat_agent_markdown


def emit_clinerules(doc: Document) -> str:
    """Emit a Document as a Cline ``.clinerules`` file."""
    return emit_flat_agent_markdown(doc)


__all__ = ["emit_clinerules"]
