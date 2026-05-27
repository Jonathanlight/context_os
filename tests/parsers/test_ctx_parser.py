"""Tests for the ``.ctx`` parser.

Milestone 1.2a brought the core API + 20 happy/error tests; Milestone 1.2b
adds fixture-driven coverage, did-you-mean hints, type errors, and the
round-trip property.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from contextos.ast.common import Severity
from contextos.parsers import (
    ContextOSParseError,
    dump_ctx_string,
    parse_ctx_file,
    parse_ctx_string,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "ctx"
VALID_FIXTURES = sorted((FIXTURES_DIR / "valid").glob("*.ctx"))
INVALID_FIXTURES = sorted((FIXTURES_DIR / "invalid").glob("*.ctx"))


def _fixture_id(path: Path) -> str:
    return path.stem


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
        with pytest.raises(ContextOSParseError, match=r"\[\[rules\]\] entry #1"):
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
        with pytest.raises(ContextOSParseError, match="unknown field 'unknown_field'"):
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


class TestFixtures:
    """Parametrized coverage over real ``.ctx`` files in tests/fixtures/ctx/."""

    @pytest.mark.parametrize(
        "path",
        VALID_FIXTURES,
        ids=[_fixture_id(p) for p in VALID_FIXTURES],
    )
    def test_valid_fixture_parses(self, path: Path) -> None:
        doc = parse_ctx_file(path)
        assert doc.project  # every valid fixture has a non-empty project
        assert doc.agent is not None

    @pytest.mark.parametrize(
        "path",
        INVALID_FIXTURES,
        ids=[_fixture_id(p) for p in INVALID_FIXTURES],
    )
    def test_invalid_fixture_raises(self, path: Path) -> None:
        with pytest.raises(ContextOSParseError):
            parse_ctx_file(path)


class TestDidYouMean:
    """Did-you-mean hints surface for the most common typos."""

    def test_unknown_root_field_suggests_close_match(self) -> None:
        try:
            parse_ctx_string('project = "X"\nlanguges = ["Python"]')
        except ContextOSParseError as exc:
            assert "unknown root field 'languges'" in str(exc)
            assert exc.suggestion is not None
            assert "languages" in exc.suggestion
        else:
            pytest.fail("expected ContextOSParseError")

    def test_unknown_root_field_no_suggestion_for_distant_typo(self) -> None:
        try:
            parse_ctx_string('project = "X"\nzzzzz = "huh"')
        except ContextOSParseError as exc:
            assert "unknown root field 'zzzzz'" in str(exc)
            # No suggestion because no close match
            assert exc.suggestion is None
        else:
            pytest.fail("expected ContextOSParseError")

    def test_unknown_identity_field_suggests_close_match(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [identity]
            role = "r"
            athor = "typo"
            """
        ).strip()
        try:
            parse_ctx_string(bad)
        except ContextOSParseError as exc:
            assert "unknown field 'athor'" in str(exc)
            assert exc.suggestion is not None
            assert "author" in exc.suggestion
        else:
            pytest.fail("expected ContextOSParseError")

    def test_unknown_rule_field_suggests_close_match(self) -> None:
        bad = textwrap.dedent(
            """
            project = "X"
            [[rules]]
            id = "X-001"
            title = "t"
            severity = "must"
            rationle = "typo"
            """
        ).strip()
        try:
            parse_ctx_string(bad)
        except ContextOSParseError as exc:
            assert "unknown field 'rationle'" in str(exc)
            assert exc.suggestion is not None
            assert "rationale" in exc.suggestion
        else:
            pytest.fail("expected ContextOSParseError")


class TestTypeErrors:
    """Type mismatches produce a focused message naming the bad field."""

    def test_languages_as_int_array_reports_per_entry(self) -> None:
        try:
            parse_ctx_string('project = "X"\nlanguages = [1, 2, 3]')
        except ContextOSParseError as exc:
            assert "must contain only strings" in str(exc)
            assert "int" in str(exc)
        else:
            pytest.fail("expected ContextOSParseError")

    def test_languages_as_scalar_reports_array_expectation(self) -> None:
        try:
            parse_ctx_string('project = "X"\nlanguages = "not-an-array"')
        except ContextOSParseError as exc:
            assert "must be an array" in str(exc)
            assert "str" in str(exc)
        else:
            pytest.fail("expected ContextOSParseError")

    def test_identity_as_string_reports_table_expectation(self) -> None:
        try:
            parse_ctx_string('project = "X"\nidentity = "should be a table"')
        except ContextOSParseError as exc:
            assert "[identity]" in str(exc)
            assert "TOML table" in str(exc)
        else:
            pytest.fail("expected ContextOSParseError")


class TestRoundTrip:
    """``parse → dump → parse`` yields a Document equal modulo positions."""

    def test_full_ctx_round_trips(self) -> None:
        original = parse_ctx_string(FULL_CTX)
        dumped = dump_ctx_string(original)
        reparsed = parse_ctx_string(dumped)
        assert _strip_positions(original) == _strip_positions(reparsed)

    def test_minimal_ctx_round_trips(self) -> None:
        original = parse_ctx_string(MINIMAL_CTX)
        dumped = dump_ctx_string(original)
        reparsed = parse_ctx_string(dumped)
        assert _strip_positions(original) == _strip_positions(reparsed)

    @pytest.mark.parametrize(
        "path",
        VALID_FIXTURES,
        ids=[_fixture_id(p) for p in VALID_FIXTURES],
    )
    def test_valid_fixtures_round_trip(self, path: Path) -> None:
        original = parse_ctx_file(path)
        dumped = dump_ctx_string(original)
        reparsed = parse_ctx_string(dumped)
        assert _strip_positions(original) == _strip_positions(reparsed)

    def test_dump_preserves_rule_order(self) -> None:
        original = parse_ctx_string(FULL_CTX)
        dumped = dump_ctx_string(original)
        reparsed = parse_ctx_string(dumped)
        assert original.agent is not None
        assert reparsed.agent is not None
        assert [r.id for r in original.agent.rules] == [r.id for r in reparsed.agent.rules]


def _strip_positions(doc: object) -> dict[str, Any]:
    """Dump a Document modulo per-rule ``position`` fields.

    Positions reflect line numbers in the original source; they will differ
    after a round-trip because ``dump_ctx_string`` is not byte-stable for
    whitespace. Semantic round-trip is what we test here.
    """
    dump: dict[str, Any] = doc.model_dump()  # type: ignore[attr-defined]
    agent = dump.get("agent")
    if isinstance(agent, dict) and "rules" in agent:
        for rule in agent["rules"]:
            rule.pop("position", None)
    return dump
