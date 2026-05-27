"""Parsers for ContextOS source formats.

Milestone 1.2a ships the ``.ctx`` parser (the canonical TOML source). The
Markdown parser for existing agent files (CLAUDE.md / AGENTS.md / …) lands
in Milestone 1.4. RAG (Phase 6) and Skill (Phase 5) parsers come later.
"""

from __future__ import annotations

from contextos.parsers.ctx_parser import (
    ContextOSParseError,
    dump_ctx_string,
    parse_ctx_file,
    parse_ctx_string,
)
from contextos.parsers.markdown_parser import (
    SUPPORTED_TARGETS,
    parse_markdown_file,
    parse_markdown_string,
)

__all__ = [
    "SUPPORTED_TARGETS",
    "ContextOSParseError",
    "dump_ctx_string",
    "parse_ctx_file",
    "parse_ctx_string",
    "parse_markdown_file",
    "parse_markdown_string",
]
