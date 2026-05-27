"""rustc-style CLI renderer for diagnostics.

Output shape (color stripped here for clarity)::

    error[S001]: description too vague
      --> skills/pdf-extract/SKILL.md:3:14
       |
     3 | description: extract data
       |              ^^^^^^^^^^^^
       |
       = help: describe the input shape and the output shape concretely
       = doc:  https://contextos.dev/rules/S001

Colors are emitted as ANSI escape sequences when ``color=True``. The CLI
turns ``color`` off when stdout is not a TTY so piping to ``grep`` or a
file produces plain text.

This module does **not** import :mod:`rich`. ANSI is enough for what we
ship in Phase 1; if we later want true terminal capability detection
(Windows console support, 256-color palettes), we can layer rich on top
without changing this module's public API.
"""

from __future__ import annotations

from contextos.diagnostics.diagnostic import Diagnostic, DiagnosticBag, DiagSeverity

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"

_SEVERITY_COLOR: dict[DiagSeverity, str] = {
    DiagSeverity.ERROR: "\033[31m",  # red
    DiagSeverity.WARNING: "\033[33m",  # yellow
    DiagSeverity.INFO: "\033[34m",  # blue
}


def render_cli(
    diagnostic: Diagnostic,
    *,
    source_text: str | None = None,
    color: bool = False,
) -> str:
    """Render a single diagnostic. Returns a plain string (with optional ANSI).

    ``source_text`` enables the underlined-line preview. When omitted, only
    the header + hint lines are produced. The caller is responsible for
    reading the file content — keeping I/O out of this module makes the
    renderer trivially testable.
    """
    parts: list[str] = []
    parts.append(_header(diagnostic, color=color))
    if diagnostic.position is not None:
        parts.append(_location(diagnostic, color=color))
        if source_text is not None:
            preview = _line_preview(diagnostic, source_text, color=color)
            if preview is not None:
                parts.append(preview)
    if diagnostic.suggestion is not None:
        parts.append(_aside("help", diagnostic.suggestion, color=color))
    if diagnostic.doc_url is not None:
        parts.append(_aside("doc", diagnostic.doc_url, color=color))
    return "\n".join(parts)


def render_cli_many(bag: DiagnosticBag, *, color: bool = False) -> str:
    """Render every diagnostic in :class:`DiagnosticBag` order, blank-line-separated."""
    return "\n\n".join(render_cli(d, color=color) for d in bag.sorted())


def _header(diagnostic: Diagnostic, *, color: bool) -> str:
    severity = diagnostic.severity.value
    code = diagnostic.code
    message = diagnostic.message
    if color:
        sev_color = _SEVERITY_COLOR[diagnostic.severity]
        return f"{_BOLD}{sev_color}{severity}[{code}]{_RESET}{_BOLD}: {message}{_RESET}"
    return f"{severity}[{code}]: {message}"


def _location(diagnostic: Diagnostic, *, color: bool) -> str:
    assert diagnostic.position is not None  # guarded by caller
    pos = diagnostic.position
    location = f"{pos.file or '<unknown>'}:{pos.line}:{pos.column}"
    arrow = "  -->"
    if color:
        return f"{_CYAN}{arrow}{_RESET} {location}"
    return f"{arrow} {location}"


def _aside(label: str, content: str, *, color: bool) -> str:
    """``= help: …`` / ``= doc: …`` lines under a diagnostic."""
    if color:
        return f"   {_DIM}= {label}:{_RESET} {content}"
    return f"   = {label}: {content}"


def _line_preview(
    diagnostic: Diagnostic,
    source_text: str,
    *,
    color: bool,
) -> str | None:
    """Render the offending line with a caret pointing at the column.

    Returns ``None`` if the position's line is out of range (e.g. when the
    source has been edited since the diagnostic was produced).
    """
    assert diagnostic.position is not None
    pos = diagnostic.position
    lines = source_text.splitlines()
    if pos.line < 1 or pos.line > len(lines):
        return None
    line_text = lines[pos.line - 1]
    line_no = str(pos.line)
    gutter_width = len(line_no)
    blank_gutter = " " * gutter_width
    underline = " " * (pos.column - 1) + "^"

    if color:
        bar = f"{_CYAN}|{_RESET}"
        sev_color = _SEVERITY_COLOR[diagnostic.severity]
        underline_line = f"   {blank_gutter} {bar} {_BOLD}{sev_color}{underline}{_RESET}"
        return "\n".join(
            [
                f"   {blank_gutter} {bar}",
                f"   {_CYAN}{line_no}{_RESET} {bar} {line_text}",
                underline_line,
            ]
        )
    return "\n".join(
        [
            f"   {blank_gutter} |",
            f"   {line_no} | {line_text}",
            f"   {blank_gutter} | {underline}",
        ]
    )
