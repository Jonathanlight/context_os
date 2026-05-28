"""Tests for the domain TextEdit + apply helpers — Phase 8.5."""

from __future__ import annotations

import pytest

from contextos.fix.edit import TextEdit, apply_text_edit, apply_text_edits


def _edit(
    *,
    start: tuple[int, int] = (0, 0),
    end: tuple[int, int] | None = None,
    new_text: str = "",
) -> TextEdit:
    if end is None:
        end = start
    return TextEdit(
        start_line=start[0],
        start_column=start[1],
        end_line=end[0],
        end_column=end[1],
        new_text=new_text,
    )


class TestApplyTextEdit:
    def test_insertion_at_start(self) -> None:
        text = "hello\nworld\n"
        out = apply_text_edit(text, _edit(new_text="X"))
        assert out == "Xhello\nworld\n"

    def test_insertion_mid_line(self) -> None:
        text = "hello\nworld\n"
        out = apply_text_edit(text, _edit(start=(0, 2), new_text="X"))
        assert out == "heXllo\nworld\n"

    def test_replacement_single_line(self) -> None:
        text = "hello\nworld\n"
        out = apply_text_edit(text, _edit(start=(0, 0), end=(0, 5), new_text="bye"))
        assert out == "bye\nworld\n"

    def test_deletion(self) -> None:
        text = "hello\nworld\n"
        out = apply_text_edit(text, _edit(start=(0, 0), end=(0, 5)))
        assert out == "\nworld\n"

    def test_multi_line_replacement(self) -> None:
        text = "ab\ncd\nef\n"
        out = apply_text_edit(text, _edit(start=(0, 1), end=(2, 1), new_text="XY"))
        assert out == "aXYf\n"

    def test_negative_range_rejected(self) -> None:
        edit = _edit(start=(0, 5), end=(0, 2), new_text="x")
        with pytest.raises(ValueError, match=r"precedes start"):
            apply_text_edit("hello\n", edit)


class TestApplyTextEdits:
    def test_no_edits_returns_input(self) -> None:
        assert apply_text_edits("hello\n", []) == "hello\n"

    def test_two_non_overlapping_edits(self) -> None:
        text = "abcdef\nghijkl\n"
        edits = [
            _edit(start=(0, 0), end=(0, 1), new_text="A"),  # 'a' -> 'A'
            _edit(start=(1, 0), end=(1, 1), new_text="G"),  # 'g' -> 'G'
        ]
        out = apply_text_edits(text, edits)
        assert out == "Abcdef\nGhijkl\n"

    def test_edits_applied_back_to_front(self) -> None:
        text = "abcdef\n"
        # Two edits on the same line — earlier ones must not shift later ones.
        edits = [
            _edit(start=(0, 1), end=(0, 2), new_text="XX"),  # insert at col 1
            _edit(start=(0, 4), end=(0, 5), new_text="YY"),  # at col 4
        ]
        out = apply_text_edits(text, edits)
        assert out == "aXXcdYYf\n"

    def test_overlapping_edits_rejected(self) -> None:
        edits = [
            _edit(start=(0, 0), end=(0, 3), new_text="X"),
            _edit(start=(0, 2), end=(0, 5), new_text="Y"),
        ]
        with pytest.raises(ValueError, match=r"overlapping"):
            apply_text_edits("abcdef\n", edits)


class TestEdgeCases:
    def test_empty_text_with_insertion(self) -> None:
        assert apply_text_edit("", _edit(new_text="x")) == "x"

    def test_negative_coords_rejected(self) -> None:
        with pytest.raises(ValueError):
            TextEdit(
                start_line=-1, start_column=0, end_line=0, end_column=0, new_text=""
            )
