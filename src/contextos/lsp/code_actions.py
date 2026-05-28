"""LSP code actions — turn diagnostic suggestions into editor quick-fixes.

The editor calls ``textDocument/codeAction`` with a range and the
diagnostics inside it. We respond with a list of :class:`CodeAction`
items the user can pick from a lightbulb menu.

Phase 7.3 ships two tiers of code actions:

1. **Info-only quick-fix** — every diagnostic that carries a
   non-empty ``suggestion`` produces an action whose ``title`` is the
   suggestion's first line. There is no ``edit`` attached, so clicking
   it just dismisses the menu; the value is purely UX surface —
   surfacing the suggestion in the editor's quick-fix area in addition
   to the diagnostic hover.

2. **Structured fix** for rules where the transform is unambiguous.
   Today we ship one: **X003** (question instead of directive) — strip
   the trailing ``?`` from the rule title. The fix produces a real
   :class:`TextEdit` the editor applies on click.

Future PRs extend the structured-fix table without touching the
dispatcher.
"""

from __future__ import annotations

import re

from lsprotocol import types as lsp

_X003_TITLE_PATTERN = re.compile(r'(?P<lead>^\s*title\s*=\s*"[^"]*)\?(?P<trail>"\s*)$')
"""Match a TOML ``title = "...?"`` line so the trailing ``?`` can be
sliced out. Two capture groups bracket the question mark so the
replacement is just the empty string at a known offset."""


def compute_code_actions(
    text: str,
    diagnostics: list[lsp.Diagnostic],
    uri: str,
) -> list[lsp.CodeAction]:
    """Compose code actions from the diagnostics inside the requested range.

    Order: structured fixes first (they're more valuable than info-only
    titles when both apply to the same diagnostic), then info-only
    fallbacks for every diagnostic carrying a suggestion.
    """
    actions: list[lsp.CodeAction] = []
    for diag in diagnostics:
        structured = _structured_fix(text, diag, uri)
        if structured is not None:
            actions.append(structured)
        actions.extend(_info_only(diag))
    return actions


def _info_only(diag: lsp.Diagnostic) -> list[lsp.CodeAction]:
    """Info-only quick-fix for any diagnostic with a non-empty suggestion.

    The diagnostic's message already carries ``help: <suggestion>``
    appended by the diagnostics adapter. Code actions duplicate the
    info into the editor's lightbulb menu so users see it without
    hovering the diagnostic marker.
    """
    suggestion = _extract_suggestion(diag.message)
    if not suggestion:
        return []
    code = diag.code if isinstance(diag.code, str) else ""
    title = f"{code}: {_first_line(suggestion)}" if code else _first_line(suggestion)
    return [
        lsp.CodeAction(
            title=title,
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diag],
        )
    ]


def _structured_fix(
    text: str,
    diag: lsp.Diagnostic,
    uri: str,
) -> lsp.CodeAction | None:
    """Dispatch a structured fix by diagnostic code, or return None.

    Adding a structured fix is a single ``elif`` branch in this
    function plus a corresponding builder helper. The dispatcher
    intentionally keeps the rule-id check explicit so a future PR
    sees the full list of supported transforms in one place.
    """
    if diag.code == "X003":
        return _build_x003_fix(text, diag, uri)
    return None


def _build_x003_fix(
    text: str,
    diag: lsp.Diagnostic,
    uri: str,
) -> lsp.CodeAction | None:
    """Strip the trailing ``?`` from a rule title.

    Walks the source from the diagnostic's reported line forward (the
    position points at the ``[[rules]]`` header; the offending title
    sits a few lines below). We stop at the next blank line or
    section header to avoid mis-editing an unrelated rule.
    """
    lines = text.splitlines()
    start_line = diag.range.start.line
    title_line_index = _find_title_line(lines, start_line)
    if title_line_index is None:
        return None
    match = _X003_TITLE_PATTERN.match(lines[title_line_index])
    if match is None:
        return None
    # Compute the column of the '?' so the TextEdit deletes exactly
    # that character (and nothing around it). The capture groups give
    # us a clean offset.
    question_column = match.start("trail") - 1
    edit_range = lsp.Range(
        start=lsp.Position(line=title_line_index, character=question_column),
        end=lsp.Position(line=title_line_index, character=question_column + 1),
    )
    workspace_edit = lsp.WorkspaceEdit(
        changes={
            uri: [lsp.TextEdit(range=edit_range, new_text="")],
        }
    )
    return lsp.CodeAction(
        title="X003: drop the trailing '?'",
        kind=lsp.CodeActionKind.QuickFix,
        diagnostics=[diag],
        edit=workspace_edit,
        is_preferred=True,
    )


def _find_title_line(lines: list[str], start: int) -> int | None:
    """Scan forward from ``start`` looking for a ``title = "...?"`` line.

    The diagnostic position commonly lands on the ``[[rules]]``
    header itself; we skip that first line when checking the
    "new-section boundary" so the scan can reach the title a few
    lines below. After the first line, hitting a blank line or
    another section header bails — we don't want to cross into a
    sibling rule's block.
    """
    for offset in range(8):  # look ahead 8 lines max
        idx = start + offset
        if idx >= len(lines):
            return None
        line = lines[idx]
        if _X003_TITLE_PATTERN.match(line):
            return idx
        if offset == 0:
            continue  # diagnostic line is allowed to be a section header
        stripped = line.strip()
        if not stripped or stripped.startswith("["):
            return None
    return None


def _extract_suggestion(message: str) -> str | None:
    """Pull the ``help: ...`` portion out of a composed diagnostic message.

    The diagnostics adapter (Phase 7.1) composes
    ``"{message}\\n\\nhelp: {suggestion}"`` when a suggestion is
    present. We split on the ``help:`` marker to recover the
    suggestion text; missing marker means no suggestion to surface.
    """
    marker = "help:"
    idx = message.find(marker)
    if idx < 0:
        return None
    return message[idx + len(marker) :].strip()


def _first_line(text: str) -> str:
    """Return the first non-empty line of ``text``, stripped."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


__all__ = ["compute_code_actions"]
