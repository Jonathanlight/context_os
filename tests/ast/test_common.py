"""Tests for shared AST types."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.ast.common import Position, ProseBlock, Severity


class TestSeverity:
    def test_values_are_lowercase_strings(self) -> None:
        assert Severity.MUST.value == "must"
        assert Severity.SHOULD.value == "should"
        assert Severity.MAY.value == "may"

    def test_str_enum_compares_to_raw_string(self) -> None:
        # StrEnum members are also str instances, so the comparison holds at
        # runtime even though mypy considers the operands non-overlapping.
        assert str(Severity.MUST) == "must"

    def test_rejects_unknown_value(self) -> None:
        with pytest.raises(ValueError, match="maybe"):
            Severity("maybe")


class TestPosition:
    def test_minimal_position_with_just_line(self) -> None:
        p = Position(line=42)
        assert p.line == 42
        assert p.column == 1
        assert p.file is None

    def test_full_position(self) -> None:
        p = Position(file="CLAUDE.md", line=7, column=3)
        assert p.file == "CLAUDE.md"
        assert p.line == 7
        assert p.column == 3

    def test_line_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Position(line=0)

    def test_column_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Position(line=1, column=0)

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="offset"):
            Position(line=1, offset=10)  # type: ignore[call-arg]

    def test_is_frozen(self) -> None:
        p = Position(line=1)
        with pytest.raises(ValidationError):
            p.line = 2  # type: ignore[misc]

    def test_round_trips_via_json(self) -> None:
        original = Position(file="x.md", line=5, column=2)
        restored = Position.model_validate_json(original.model_dump_json())
        assert restored == original


class TestProseBlock:
    def test_minimal_prose_block(self) -> None:
        block = ProseBlock(content="Some prose between sections.")
        assert block.content == "Some prose between sections."
        assert block.position is None

    def test_prose_block_with_position(self) -> None:
        pos = Position(line=10)
        block = ProseBlock(content="Hi", position=pos)
        assert block.position == pos

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProseBlock(content="")

    def test_round_trips_via_json(self) -> None:
        original = ProseBlock(content="Hello", position=Position(line=3))
        restored = ProseBlock.model_validate_json(original.model_dump_json())
        assert restored == original
