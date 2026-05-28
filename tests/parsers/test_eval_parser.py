"""Tests for the .eval.toml parser — Phase 7.7."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from contextos.parsers import (
    ContextOSParseError,
    parse_eval_file,
    parse_eval_string,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "eval"


class TestSkillSuiteParsing:
    def test_minimal_skill_suite(self) -> None:
        suite = parse_eval_file(FIXTURES / "skill_minimal.eval.toml")
        assert suite.project == "PdfExtract"
        assert suite.target == "anthropic_skill"
        assert len(suite.skill_cases) == 1
        case = suite.skill_cases[0]
        assert case.name == "happy-path"
        assert case.expected_skill == "pdf-extract"

    def test_full_skill_suite_preserves_order(self) -> None:
        suite = parse_eval_file(FIXTURES / "skill_full.eval.toml")
        assert len(suite.skill_cases) == 3
        names = [c.name for c in suite.skill_cases]
        assert names == ["happy-path-en", "happy-path-fr", "negative-routing"]

    def test_tags_preserved(self) -> None:
        suite = parse_eval_file(FIXTURES / "skill_full.eval.toml")
        en_case = next(c for c in suite.skill_cases if c.name == "happy-path-en")
        assert en_case.tags == ["en", "happy-path"]


class TestRagSuiteParsing:
    def test_minimal_rag_suite(self) -> None:
        suite = parse_eval_file(FIXTURES / "rag_minimal.eval.toml")
        assert suite.target == "rag"
        assert len(suite.rag_cases) == 1
        case = suite.rag_cases[0]
        assert case.query.startswith("What is")
        assert case.top_k == 5


class TestStringParsing:
    def test_parses_inline_string(self) -> None:
        text = textwrap.dedent(
            """\
            project = "Inline"
            target = "anthropic_skill"

            [[skill_case]]
            name = "trivial"
            prompt = "Run the demo."
            expected_skill = "demo-runner"
            """
        )
        suite = parse_eval_string(text)
        assert suite.project == "Inline"
        assert len(suite.skill_cases) == 1


class TestErrorPaths:
    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ContextOSParseError, match=r"cannot read file"):
            parse_eval_file(tmp_path / "missing.eval.toml")

    def test_invalid_toml(self) -> None:
        with pytest.raises(ContextOSParseError, match=r"invalid TOML"):
            parse_eval_string("project = ")

    def test_unknown_root_field(self) -> None:
        text = textwrap.dedent(
            """\
            project = "X"
            target = "rag"
            project_name = "Oops"

            [[rag_case]]
            name = "x"
            query = "y"
            expected_sources = ["z"]
            """
        )
        with pytest.raises(ContextOSParseError, match=r"unknown root field"):
            parse_eval_string(text)

    def test_case_as_table_not_aot(self) -> None:
        # Single bracket [skill_case] instead of double.
        text = textwrap.dedent(
            """\
            project = "X"
            target = "anthropic_skill"

            [skill_case]
            name = "x"
            prompt = "y"
            expected_skill = "z"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"array-of-tables"):
            parse_eval_string(text)

    def test_missing_required_field(self) -> None:
        text = textwrap.dedent(
            """\
            project = "X"
            target = "anthropic_skill"

            [[skill_case]]
            name = "incomplete"
            prompt = "no expected_skill set"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"validation"):
            parse_eval_string(text)

    def test_unknown_target_rejected(self) -> None:
        text = textwrap.dedent(
            """\
            project = "X"
            target = "claude_code"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"validation"):
            parse_eval_string(text)

    def test_target_skill_with_rag_cases_rejected(self) -> None:
        text = textwrap.dedent(
            """\
            project = "X"
            target = "anthropic_skill"

            [[skill_case]]
            name = "a"
            prompt = "b"
            expected_skill = "c"

            [[rag_case]]
            name = "x"
            query = "y"
            expected_sources = ["z"]
            """
        )
        with pytest.raises(ContextOSParseError, match=r"validation"):
            parse_eval_string(text)


class TestEmptySuite:
    def test_no_cases_parses(self) -> None:
        # A placeholder eval file under construction.
        text = textwrap.dedent(
            """\
            project = "Wip"
            target = "anthropic_skill"
            """
        )
        suite = parse_eval_string(text)
        assert suite.total_cases() == 0
