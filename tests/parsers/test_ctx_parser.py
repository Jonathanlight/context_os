"""Tests for the ``.ctx`` parser (Milestone 1.2a — core happy path + key errors)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from contextos.ast.common import Severity
from contextos.parsers import (
    ContextOSParseError,
    parse_ctx_file,
    parse_ctx_string,
)

MINIMAL_CTX = textwrap.dedent(
    """
    project = "MyApp"
    artifacts = ["context"]
    """
).strip()

FULL_CTX = textwrap.dedent(
    """
    project = "MyApp"
    ctx_version = "0.3"
    artifacts = ["context"]
    languages = ["Python", "Rust"]
    authors = ["Jonathan KABLAN"]
    version = "1.2.3"

    forbidden_patterns = ["raw SQL strings", "wildcard imports"]

    [identity]
    role = "senior"
    context = "internal tooling"
    author = "Jonathan KABLAN"

    [stack]
    required = ["python>=3.12"]
    forbidden = ["django"]
    preferred = ["fastapi"]

    [style]
    conventions = ["4 spaces", "snake_case"]

    [tools]
    required = ["ruff", "mypy"]
    forbidden = ["black"]

    [[rules]]
    id = "TDD-001"
    title = "Tests before code"
    severity = "must"
    tags = ["testing"]

    [[rules]]
    id = "SEC-042"
    title = "Sanitize input"
    severity = "should"
    rationale = "prevent injection"
    """
).strip()


class TestParseHappyPath:
    def test_minimal_ctx_yields_project_and_empty_agent(self) -> None:
        doc = parse_ctx_string(MINIMAL_CTX)
        assert doc.project == "MyApp"
        assert doc.type == "agent"
        assert doc.agent is not None
        assert doc.agent.rules == []

    def test_full_ctx_populates_every_section(self) -> None:
        doc = parse_ctx_string(FULL_CTX)
        assert doc.project == "MyApp"
        assert doc.ctx_version == "0.3"
        assert doc.languages == ["Python", "Rust"]
        assert doc.authors == ["Jonathan KABLAN"]
        assert doc.version == "1.2.3"

        a = doc.agent
        assert a is not None
        assert a.identity is not None
        assert a.identity.role == "senior"
        assert a.stack is not None
        assert a.stack.required == ["python>=3.12"]
        assert a.style is not None
        assert "snake_case" in a.style.conventions
        assert a.tools is not None
        assert a.tools.forbidden == ["black"]
        assert a.forbidden_patterns == ["raw SQL strings", "wildcard imports"]
        assert len(a.rules) == 2
        assert a.rules[0].id == "TDD-001"
        assert a.rules[0].severity == Severity.MUST
        assert a.rules[1].id == "SEC-042"
        assert a.rules[1].rationale == "prevent injection"

    def test_rules_carry_line_positions(self) -> None:
        doc = parse_ctx_string(FULL_CTX, source="my.ctx")
        assert doc.agent is not None
        first, second = doc.agent.rules
        assert first.position is not None
        assert second.position is not None
        assert first.position.line < second.position.line
        assert first.position.file == "my.ctx"

    def test_default_source_yields_position_without_file(self) -> None:
        doc = parse_ctx_string(FULL_CTX)
        assert doc.agent is not None
        assert doc.agent.rules[0].position is not None
        assert doc.agent.rules[0].position.file is None

    def test_artifacts_defaults_to_context_when_absent(self) -> None:
        doc = parse_ctx_string('project = "X"')
        assert doc.project == "X"


class TestParseFile:
    def test_parse_ctx_file_round_trips_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "sample.ctx"
        path.write_text(FULL_CTX, encoding="utf-8")
        doc = parse_ctx_file(path)
        assert doc.project == "MyApp"
        assert doc.agent is not None
        assert doc.agent.rules[0].position is not None
        assert doc.agent.rules[0].position.file == str(path)

    def test_missing_file_raises_with_source(self, tmp_path: Path) -> None:
        path = tmp_path / "does_not_exist.ctx"
        with pytest.raises(ContextOSParseError) as info:
            parse_ctx_file(path)
        assert info.value.source == str(path)


class TestParseErrors:
    def test_invalid_toml_is_reported(self) -> None:
        with pytest.raises(ContextOSParseError, match="invalid TOML"):
            parse_ctx_string("project = [unterminated")

    def test_missing_project_is_reported(self) -> None:
        with pytest.raises(ContextOSParseError, match="missing or empty"):
            parse_ctx_string('artifacts = ["context"]')

    def test_empty_project_string_is_reported(self) -> None:
        with pytest.raises(ContextOSParseError, match="missing or empty"):
            parse_ctx_string('project = "   "')

    def test_artifacts_must_be_non_empty_list(self) -> None:
        with pytest.raises(ContextOSParseError, match="non-empty array"):
            parse_ctx_string('project = "X"\nartifacts = []')

    def test_unsupported_artifact_is_reported(self) -> None:
        with pytest.raises(ContextOSParseError, match="unsupported artifact"):
            parse_ctx_string('project = "X"\nartifacts = ["context", "skills"]')

    def test_rules_with_unknown_severity_is_reported(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [[rules]]
            id = "X-001"
            title = "t"
            severity = "maybe"
            """
        ).strip()
        with pytest.raises(ContextOSParseError, match="unknown severity 'maybe'"):
            parse_ctx_string(bad)

    def test_rules_with_missing_severity_is_reported(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [[rules]]
            id = "X-001"
            title = "t"
            """
        ).strip()
        with pytest.raises(ContextOSParseError, match="missing 'severity'"):
            parse_ctx_string(bad)

    def test_rules_with_invalid_id_is_reported(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [[rules]]
            id = "lowercase-001"
            title = "t"
            severity = "may"
            """
        ).strip()
        with pytest.raises(ContextOSParseError, match=r"invalid \[\[rules\]\] entry"):
            parse_ctx_string(bad)

    def test_unknown_field_in_identity_is_reported(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [identity]
            role = "r"
            unknown_field = "x"
            """
        ).strip()
        with pytest.raises(ContextOSParseError, match=r"invalid \[identity\]"):
            parse_ctx_string(bad)

    def test_languages_must_be_strings(self) -> None:
        bad = 'project = "X"\nlanguages = [1, 2, 3]'
        with pytest.raises(ContextOSParseError, match="must contain only strings"):
            parse_ctx_string(bad)


class TestErrorRendering:
    def test_error_message_includes_source(self) -> None:
        try:
            parse_ctx_string("", source="foo.ctx")
        except ContextOSParseError as exc:
            assert "foo.ctx" in str(exc)
        else:
            pytest.fail("expected ContextOSParseError")

    def test_error_message_includes_position_when_present(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [[rules]]
            id = "X-001"
            title = "t"
            severity = "maybe"
            """
        ).strip()
        try:
            parse_ctx_string(bad, source="my.ctx")
        except ContextOSParseError as exc:
            rendered = str(exc)
            assert "my.ctx:" in rendered
            assert "unknown severity" in rendered
        else:
            pytest.fail("expected ContextOSParseError")

    def test_error_message_includes_suggestion(self) -> None:
        try:
            parse_ctx_string('artifacts = ["context"]')
        except ContextOSParseError as exc:
            assert exc.suggestion is not None
            assert "YourProjectName" in exc.suggestion
        else:
            pytest.fail("expected ContextOSParseError")
