"""LSP hover logic — surface rule documentation when the cursor sits on a code.

Pure module (no pygls runtime — only ``lsprotocol.types``) so the
unit tests don't need a server fixture. The public entry point is
:func:`compute_hover` which takes (text, position) and returns either
an ``lsp.Hover`` carrying a Markdown blob, or ``None`` when no rule
code is under the cursor.

A rule code is detected by the conservative regex
``^[A-Z]{1,2}\\d{3,}$`` matching the token under the cursor. Diagnostic
strings frequently embed codes (``warning[A001]: ...``) so we extract
the token using a word-boundary tokenizer, not the file's text raw.
"""

from __future__ import annotations

import re

from lsprotocol import types as lsp

_RULE_CODE_PATTERN = re.compile(r"\b([A-Z]{1,2}\d{3,})\b")
"""Match a ContextOS rule code anywhere in a string.

Covers A001, R001, S001, K001, X001, F001, P001, C001 (single-letter
families) and XA001 (the only two-letter family today). Future
multi-letter prefixes work without code changes.
"""

_DOC_BASE_URL = "https://contextos.dev/rules"


def compute_hover(text: str, position: lsp.Position) -> lsp.Hover | None:
    """Return hover info for the rule code at ``position``, or None.

    The hover string is Markdown so editors that render it preserve the
    formatting. We keep it intentionally short — three lines max — so it
    doesn't crowd the editor's tooltip space.
    """
    code = _token_under_cursor(text, position)
    if code is None or not _RULE_CODE_PATTERN.fullmatch(code):
        return None
    return lsp.Hover(
        contents=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown,
            value=_hover_markdown(code),
        ),
        range=_token_range(text, position, code),
    )


def _token_under_cursor(text: str, position: lsp.Position) -> str | None:
    """Pull the alphanumeric token straddling the cursor position.

    Walks left until a non-token char, then right; the resulting span
    is the token. Returns ``None`` when the cursor sits on whitespace
    or punctuation between tokens — the editor will then show no
    hover, which is the correct quiet behavior.
    """
    lines = text.splitlines()
    if position.line >= len(lines):
        return None
    line = lines[position.line]
    if position.character > len(line):
        return None
    # Expand left.
    start = position.character
    while start > 0 and _is_token_char(line[start - 1]):
        start -= 1
    # Expand right.
    end = position.character
    while end < len(line) and _is_token_char(line[end]):
        end += 1
    if start == end:
        return None
    return line[start:end]


def _is_token_char(ch: str) -> bool:
    """Return True for chars that may appear inside a rule code."""
    return ch.isalnum() or ch == "_"


def _token_range(
    text: str,
    position: lsp.Position,
    token: str,
) -> lsp.Range | None:
    """Span the token under the cursor as an LSP Range, or None.

    Used by the editor to underline the active token in the tooltip.
    None is fine if we can't recompute the span; the editor will fall
    back to highlighting the cursor position.
    """
    lines = text.splitlines()
    if position.line >= len(lines):
        return None
    line = lines[position.line]
    start = position.character
    while start > 0 and _is_token_char(line[start - 1]):
        start -= 1
    end = start + len(token)
    return lsp.Range(
        start=lsp.Position(line=position.line, character=start),
        end=lsp.Position(line=position.line, character=end),
    )


def _hover_markdown(code: str) -> str:
    """Compose the Markdown blob shown in the editor tooltip."""
    return (
        f"**{code}** — ContextOS lint rule\n\n"
        f"Open [reference docs]({_DOC_BASE_URL}/{code}) for trigger, "
        "rationale, and suggested fixes."
    )


__all__ = ["compute_hover"]
