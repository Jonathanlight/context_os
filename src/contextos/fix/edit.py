"""Domain TextEdit model + apply helper — Phase 8.5.

Decoupled from ``lsprotocol.types`` so the fix module is importable
without pygls. The LSP code-actions layer adapts these into
``lsp.TextEdit`` on the editor side; ``ctx fix`` consumes them
directly.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TextEdit(BaseModel):
    """A single replacement on a source string.

    Coordinates are 0-indexed line + character, **inclusive start**,
    **exclusive end** (matching LSP semantics). The fix module treats
    ``end_line == start_line and end_column == start_column`` as an
    insertion at that anchor.
    """

    model_config = ConfigDict(extra="forbid")

    start_line: int = Field(ge=0)
    start_column: int = Field(ge=0)
    end_line: int = Field(ge=0)
    end_column: int = Field(ge=0)
    new_text: str


def apply_text_edit(text: str, edit: TextEdit) -> str:
    """Return ``text`` with ``edit`` applied.

    Splits into lines, computes the character offsets for the start
    and end anchors, and replaces the spanned segment with
    ``edit.new_text``. The original line endings are preserved
    (``splitlines(keepends=True)`` round-trips). Inserts work
    naturally when start == end.
    """
    lines = text.splitlines(keepends=True)
    start_offset = _offset_of(lines, edit.start_line, edit.start_column)
    end_offset = _offset_of(lines, edit.end_line, edit.end_column)
    if end_offset < start_offset:
        msg = (
            f"TextEdit end ({edit.end_line}:{edit.end_column}) precedes "
            f"start ({edit.start_line}:{edit.start_column})"
        )
        raise ValueError(msg)
    return text[:start_offset] + edit.new_text + text[end_offset:]


def apply_text_edits(text: str, edits: list[TextEdit]) -> str:
    """Apply multiple edits to ``text``.

    Edits are applied from the END of the source backward so earlier
    edits don't shift the offsets later edits depend on. Overlapping
    edits are rejected — we'd need a CRDT to merge them safely, and
    the structured-fix surface is small enough that an author's
    expectation is "one fix per diagnostic, no overlap."
    """
    if not edits:
        return text
    ordered = sorted(
        edits,
        key=lambda e: (e.start_line, e.start_column, e.end_line, e.end_column),
    )
    _reject_overlaps(ordered)
    out = text
    for edit in reversed(ordered):
        out = apply_text_edit(out, edit)
    return out


def _offset_of(lines: list[str], line: int, column: int) -> int:
    """Convert (line, column) into a character offset in the joined text.

    ``line`` clamps to len(lines) so an edit that extends to EOF
    (``end_line=len(lines), end_column=0``) returns the total
    character count without error.
    """
    if line < 0 or column < 0:
        msg = f"negative coordinates not allowed: line={line}, column={column}"
        raise ValueError(msg)
    if line >= len(lines):
        return sum(len(line_text) for line_text in lines) + max(0, column)
    base = sum(len(line_text) for line_text in lines[:line])
    return base + column


def _reject_overlaps(edits: list[TextEdit]) -> None:
    """Raise ValueError if any two edits in ``edits`` overlap."""
    import itertools  # noqa: PLC0415 — narrow scope

    for left, right in itertools.pairwise(edits):
        if (right.start_line, right.start_column) < (left.end_line, left.end_column):
            msg = (
                "overlapping TextEdits: "
                f"({left.start_line}:{left.start_column}-"
                f"{left.end_line}:{left.end_column}) and "
                f"({right.start_line}:{right.start_column}-"
                f"{right.end_line}:{right.end_column})"
            )
            raise ValueError(msg)


__all__ = ["TextEdit", "apply_text_edit", "apply_text_edits"]
