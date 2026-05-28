"""Unit tests for LSP hover logic — Phase 7.2."""

from __future__ import annotations

import pytest
from lsprotocol import types as lsp

from contextos.lsp.hover import compute_hover


def _at(line: int, character: int) -> lsp.Position:
    return lsp.Position(line=line, character=character)


class TestRuleCodeHover:
    @pytest.mark.parametrize(
        "code", ["A001", "R001", "S001", "K001", "X001", "F001", "P001", "C001", "XA001"]
    )
    def test_known_code_returns_hover(self, code: str) -> None:
        text = f"warning[{code}]: vague directive"
        # Cursor in the middle of the code.
        idx = text.index(code) + 2
        hover = compute_hover(text, _at(0, idx))
        assert hover is not None
        assert isinstance(hover.contents, lsp.MarkupContent)
        assert code in hover.contents.value
        assert f"/rules/{code}" in hover.contents.value

    def test_range_covers_full_code(self) -> None:
        text = "see A001 for details"
        hover = compute_hover(text, _at(0, 5))
        assert hover is not None
        assert hover.range is not None
        start = hover.range.start
        end = hover.range.end
        assert text[start.character:end.character] == "A001"

    def test_markup_kind_is_markdown(self) -> None:
        hover = compute_hover("A001 ...", _at(0, 1))
        assert hover is not None
        assert isinstance(hover.contents, lsp.MarkupContent)
        assert hover.contents.kind == lsp.MarkupKind.Markdown


class TestNoHover:
    def test_whitespace_returns_none(self) -> None:
        assert compute_hover("  hello", _at(0, 0)) is None

    def test_unrelated_word_returns_none(self) -> None:
        assert compute_hover("hello world", _at(0, 2)) is None

    def test_partial_pattern_returns_none(self) -> None:
        # 'A01' has only 2 digits — below the 3-digit floor.
        assert compute_hover("A01", _at(0, 1)) is None

    def test_lowercase_code_returns_none(self) -> None:
        # 'a001' doesn't start with uppercase — rule codes are uppercase.
        assert compute_hover("a001", _at(0, 1)) is None

    def test_position_past_end_returns_none(self) -> None:
        assert compute_hover("A001", _at(99, 0)) is None


class TestTokenExtraction:
    def test_cursor_at_token_start(self) -> None:
        hover = compute_hover("A001 foo", _at(0, 0))
        assert hover is not None

    def test_cursor_at_token_end(self) -> None:
        hover = compute_hover("A001 foo", _at(0, 4))
        assert hover is not None

    def test_cursor_in_middle_of_compound(self) -> None:
        # `XA001` is a single token; cursor anywhere in it returns hover.
        hover = compute_hover("XA001 foo", _at(0, 2))
        assert hover is not None
        assert "XA001" in (
            hover.contents.value if isinstance(hover.contents, lsp.MarkupContent) else ""
        )
