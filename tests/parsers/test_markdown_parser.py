"""Tests for the generic Markdown parser (Milestone 1.4)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from contextos.ast.common import Severity
from contextos.parsers import (
    SUPPORTED_TARGETS,
    ContextOSParseError,
    parse_markdown_file,
    parse_markdown_string,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "claude"
CLAUDE_FIXTURES = sorted(FIXTURES_DIR.glob("*.md"))


def _fixture_id(path: Path) -> str:
    return path.stem


class TestSupportedTargets:
    def test_claude_code_is_supported(self) -> None:
        assert "claude_code" in SUPPORTED_TARGETS

    def test_unsupported_target_raises(self) -> None:
        with pytest.raises(ContextOSParseError, match="unsupported target 'gpt'"):
            parse_markdown_string("# X", target="gpt")


class TestParseFile:
    def test_parses_file_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "CLAUDE.md"
        path.write_text("# MyProject\n\n## Rules\n\n- Use type hints.\n")
        doc = parse_markdown_file(path, target="claude_code")
        assert doc.project == "MyProject"
        assert doc.agent is not None
        assert len(doc.agent.rules) == 1

    def test_missing_file_raises_with_source(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.md"
        with pytest.raises(ContextOSParseError) as info:
            parse_markdown_file(path, target="claude_code")
        assert info.value.source == str(path)


class TestProjectName:
    def test_h1_becomes_project_name(self) -> None:
        doc = parse_markdown_string("# Acme\n\n## Rules\n\n- be nice", target="claude_code")
        assert doc.project == "Acme"

    def test_no_h1_falls_back_to_source_stem(self) -> None:
        doc = parse_markdown_string(
            "## Rules\n\n- be nice", target="claude_code", source="/tmp/my-project.md"
        )
        assert doc.project == "my-project"

    def test_no_h1_no_source_falls_back_to_unknown(self) -> None:
        doc = parse_markdown_string("## Rules\n\n- be nice", target="claude_code")
        assert doc.project == "Unknown"

    def test_h2_first_does_not_become_project(self) -> None:
        doc = parse_markdown_string(
            "## Identity\n\nSomeone\n\n## Rules\n\n- x", target="claude_code"
        )
        assert doc.project == "Unknown"


class TestIdentity:
    def test_extracts_first_paragraph(self) -> None:
        md = textwrap.dedent(
            """
            # P
            ## Identity
            Senior engineer, internal tooling.

            More context follows.
            """
        )
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.identity is not None
        assert doc.agent.identity.role == "Senior engineer, internal tooling."

    def test_missing_identity_is_none(self) -> None:
        doc = parse_markdown_string("# P\n## Rules\n- x", target="claude_code")
        assert doc.agent is not None
        assert doc.agent.identity is None

    def test_identity_alias_about_me(self) -> None:
        md = "# P\n## About me\nI am the maintainer."
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.identity is not None
        assert "maintainer" in doc.agent.identity.role


class TestStack:
    def test_stack_with_sub_sections(self) -> None:
        md = textwrap.dedent(
            """
            # P
            ## Stack
            ### Required
            - python>=3.12
            ### Forbidden
            - django
            ### Preferred
            - fastapi
            """
        )
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.stack is not None
        assert doc.agent.stack.required == ["python>=3.12"]
        assert doc.agent.stack.forbidden == ["django"]
        assert doc.agent.stack.preferred == ["fastapi"]

    def test_stack_flat_collects_as_required(self) -> None:
        md = "# P\n## Stack\n- Python 3.12\n- FastAPI\n- Postgres"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.stack is not None
        assert doc.agent.stack.required == ["Python 3.12", "FastAPI", "Postgres"]

    def test_missing_stack_is_none(self) -> None:
        doc = parse_markdown_string("# P\n## Rules\n- x", target="claude_code")
        assert doc.agent is not None
        assert doc.agent.stack is None


class TestRulesAndSeverityInference:
    def test_each_bullet_becomes_a_rule(self) -> None:
        md = "# P\n## Rules\n- First\n- Second\n- Third"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert [r.title for r in doc.agent.rules] == ["First", "Second", "Third"]

    def test_generated_ids_are_sequential(self) -> None:
        md = "# P\n## Rules\n- A\n- B\n- C"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert [r.id for r in doc.agent.rules] == ["MD-001", "MD-002", "MD-003"]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Never commit secrets", Severity.MUST),
            ("Don't bypass tests", Severity.MUST),
            ("Must use type hints", Severity.MUST),
            ("Always run linting", Severity.MUST),
            ("Should prefer composition", Severity.SHOULD),
            ("Prefer functional style", Severity.SHOULD),
            ("Avoid global state", Severity.SHOULD),
            ("May add docstrings", Severity.MAY),
            ("Can extend later", Severity.MAY),
            ("Consider performance", Severity.MAY),
            ("Run the linter before commit", Severity.MUST),  # default
        ],
    )
    def test_severity_inferred_from_leading_words(self, text: str, expected: Severity) -> None:
        md = f"# P\n## Rules\n- {text}"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.rules[0].severity == expected

    def test_no_rules_section_is_empty_list(self) -> None:
        doc = parse_markdown_string("# P\n## Identity\nRole", target="claude_code")
        assert doc.agent is not None
        assert doc.agent.rules == []

    def test_rules_carry_position_with_file(self, tmp_path: Path) -> None:
        path = tmp_path / "x.md"
        path.write_text("# P\n## Rules\n- A rule")
        doc = parse_markdown_file(path, target="claude_code")
        assert doc.agent is not None
        rule = doc.agent.rules[0]
        assert rule.position is not None
        assert rule.position.file == str(path)


class TestStyleAndForbiddenAndTools:
    def test_style_conventions_extracted(self) -> None:
        md = "# P\n## Style\n- 4 spaces\n- snake_case"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.style is not None
        assert doc.agent.style.conventions == ["4 spaces", "snake_case"]

    def test_forbidden_patterns_extracted(self) -> None:
        md = "# P\n## Forbidden patterns\n- wildcard imports\n- raw SQL"
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.forbidden_patterns == ["wildcard imports", "raw SQL"]

    def test_tools_with_sub_sections(self) -> None:
        md = textwrap.dedent(
            """
            # P
            ## Tools
            ### Required
            - ruff
            - mypy
            ### Forbidden
            - black
            """
        )
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert doc.agent.tools is not None
        assert doc.agent.tools.required == ["ruff", "mypy"]
        assert doc.agent.tools.forbidden == ["black"]


class TestFalsePositives:
    def test_bullets_outside_known_sections_are_dropped(self) -> None:
        """Lists before any H2 or under an unrecognized H2 must not become rules."""
        md = textwrap.dedent(
            """
            # P

            - Floating bullet before any section.

            ## Some Random Heading

            - Not a rule.
            - Also not a rule.

            ## Rules

            - This IS a rule.
            """
        )
        doc = parse_markdown_string(md, target="claude_code")
        assert doc.agent is not None
        assert [r.title for r in doc.agent.rules] == ["This IS a rule."]


class TestFixtures:
    """Parametrized coverage over every fixture in tests/fixtures/claude/."""

    @pytest.mark.parametrize(
        "path",
        CLAUDE_FIXTURES,
        ids=[_fixture_id(p) for p in CLAUDE_FIXTURES],
    )
    def test_fixture_parses_without_error(self, path: Path) -> None:
        doc = parse_markdown_file(path, target="claude_code")
        assert doc.project  # non-empty
        assert doc.agent is not None

    def test_full_fixture_populates_every_section(self) -> None:
        path = FIXTURES_DIR / "full.md"
        doc = parse_markdown_file(path, target="claude_code")
        a = doc.agent
        assert a is not None
        assert a.identity is not None
        assert a.stack is not None
        assert a.stack.required == ["python>=3.12", "pydantic>=2.7"]
        assert a.style is not None
        assert "4 spaces, no tabs." in a.style.conventions
        assert a.tools is not None
        assert a.tools.required == ["ruff", "mypy", "pytest"]
        assert "Wildcard imports." in a.forbidden_patterns
        assert len(a.rules) == 5
        # The 5 rules cover severity inference across must/should/may + default.
        severities = [r.severity for r in a.rules]
        assert Severity.MUST in severities
        assert Severity.SHOULD in severities
        assert Severity.MAY in severities

    def test_false_positives_fixture_extracts_only_real_rules(self) -> None:
        path = FIXTURES_DIR / "false_positives.md"
        doc = parse_markdown_file(path, target="claude_code")
        assert doc.agent is not None
        assert [r.title for r in doc.agent.rules] == [
            "Use type hints on public APIs.",
            "Never disable a test to make CI pass.",
        ]
