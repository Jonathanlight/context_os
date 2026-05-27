"""Typed diagnostics that every analyzer emits.

A diagnostic carries a stable code (``S001``, ``C001``, ``XA001``…), a
severity, a free-form message, and optional position / suggestion / doc URL.
Renderers turn a bag of diagnostics into CLI or JSON output. Code authors
import :class:`Diagnostic` and :class:`DiagSeverity` directly; the
renderers are usually invoked once at the CLI boundary.
"""

from __future__ import annotations

from contextos.diagnostics.diagnostic import (
    DIAG_CODE_PATTERN,
    Diagnostic,
    DiagnosticBag,
    DiagSeverity,
)
from contextos.diagnostics.renderer_cli import render_cli, render_cli_many
from contextos.diagnostics.renderer_json import render_json, render_json_many

__all__ = [
    "DIAG_CODE_PATTERN",
    "DiagSeverity",
    "Diagnostic",
    "DiagnosticBag",
    "render_cli",
    "render_cli_many",
    "render_json",
    "render_json_many",
]
