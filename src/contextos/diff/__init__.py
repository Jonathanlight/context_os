"""Semantic diff for ContextOS documents.

Phase 3.4 ships the agent-family diff. Given two parsed Documents,
:func:`diff_documents` produces a :class:`DocumentDiff` describing what
changed at the AST level — not byte-level Markdown diff, but
rule-added / rule-removed / severity-shifted / stack-bucket-changed.

Two renderers consume the structured diff:

- :func:`render_diff_cli` — human-readable text with ``+``/``-``/``~``
  markers and section headers.
- :func:`render_diff_json` — machine-readable JSON for CI / dashboards.
"""

from __future__ import annotations

from contextos.diff.agent import (
    DocumentDiff,
    RuleDiff,
    StackDiff,
    ToolsDiff,
    diff_documents,
)
from contextos.diff.renderer import render_diff_cli, render_diff_json

__all__ = [
    "DocumentDiff",
    "RuleDiff",
    "StackDiff",
    "ToolsDiff",
    "diff_documents",
    "render_diff_cli",
    "render_diff_json",
]
