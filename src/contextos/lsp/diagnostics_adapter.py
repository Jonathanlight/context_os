"""Convert ContextOS diagnostics to LSP diagnostics.

Kept pure (no pygls runtime import — only ``lsprotocol.types``) so the
unit tests don't need a full LSP server. Phase 7.1's only public entry
point is :func:`to_lsp_diagnostic`; later milestones may add quick-fix
mapping built on the same shape.

Two coordinate systems collide here:

- ContextOS :class:`Position` uses **1-indexed** line / column to
  match what the CLI prints (``file:line:col``).
- LSP uses **0-indexed** line / character.

The adapter handles the off-by-one and also synthesizes a one-character
zero-length range when no Position is attached (so the editor still
highlights the start of the file rather than nothing).
"""

from __future__ import annotations

from lsprotocol import types as lsp

from contextos.ast.common import Position
from contextos.diagnostics import Diagnostic, DiagSeverity

_SEVERITY_MAP: dict[DiagSeverity, lsp.DiagnosticSeverity] = {
    DiagSeverity.ERROR: lsp.DiagnosticSeverity.Error,
    DiagSeverity.WARNING: lsp.DiagnosticSeverity.Warning,
    DiagSeverity.INFO: lsp.DiagnosticSeverity.Information,
}


def to_lsp_diagnostic(diag: Diagnostic) -> lsp.Diagnostic:
    """Render a single :class:`Diagnostic` as an LSP diagnostic.

    The LSP ``range`` is computed from :attr:`Diagnostic.position`. If
    the position is missing, the range collapses to the very start of
    the file — the editor will still surface the issue, just without a
    precise inline marker.
    """
    return lsp.Diagnostic(
        range=_range_for(diag.position),
        message=_compose_message(diag),
        severity=_SEVERITY_MAP[diag.severity],
        code=diag.code,
        code_description=(lsp.CodeDescription(href=diag.doc_url) if diag.doc_url else None),
        source="contextos",
    )


def _range_for(position: Position | None) -> lsp.Range:
    """Build an LSP Range from a ContextOS Position (1-indexed → 0-indexed).

    LSP's ``end`` is exclusive; we collapse to a zero-length range at
    the start position so the editor underlines just that anchor.
    Later milestones may widen the range using a real lexer span.
    """
    if position is None:
        zero = lsp.Position(line=0, character=0)
        return lsp.Range(start=zero, end=zero)
    line = max(0, position.line - 1)
    character = max(0, position.column - 1)
    anchor = lsp.Position(line=line, character=character)
    return lsp.Range(start=anchor, end=anchor)


def _compose_message(diag: Diagnostic) -> str:
    """Assemble the message + suggestion shown in the editor hover.

    LSP renders the diagnostic message as a single string; the
    ``code_description`` carries the doc URL separately. We keep the
    suggestion inline so the user sees the fix without clicking through.
    """
    if diag.suggestion:
        return f"{diag.message}\n\nhelp: {diag.suggestion}"
    return diag.message


__all__ = ["to_lsp_diagnostic"]
