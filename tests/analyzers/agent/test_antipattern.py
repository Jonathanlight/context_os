"""Tests for the X* anti-pattern rules."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import antipattern
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _rule(title: str, rule_id: str = "X-001") -> Rule:
    return Rule(
        id=rule_id,
        title=title,
        severity=Severity.MUST,
        position=Position(file="x.md", line=10),
    )


def _codes_for(title: str) -> list[str]:
    return [d.code for d in antipattern.check(AgentDocument(rules=[_rule(title)]))]


class TestX001PlaceholderMarker:
    @pytest.mark.parametrize(
        "title",
        [
            "TODO: Decide on the timeout policy",
            "todo finish this",
            "Fix the validation chain (FIXME)",
            "XXX: This is a hack",
            "Use prepared statements (HACK around DB driver bug)",
        ],
    )
    def test_detects_markers(self, title: str) -> None:
        assert "X001" in _codes_for(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Use TODO-list discipline for branching tasks",
            "Test the today function",  # "today" contains 'tod' but no whole-token TODO
            "Use type hints on every public function",
        ],
    )
    def test_does_not_flag_substring_matches(self, title: str) -> None:
        assert "X001" not in _codes_for(title)

    def test_message_names_marker(self) -> None:
        diags = list(antipattern.check(AgentDocument(rules=[_rule("TODO: finish me")])))
        x001 = next(d for d in diags if d.code == "X001")
        assert "'TODO'" in x001.message

    def test_severity_is_warning(self) -> None:
        diags = list(antipattern.check(AgentDocument(rules=[_rule("TODO: finish me")])))
        x001 = next(d for d in diags if d.code == "X001")
        assert x001.severity == DiagSeverity.WARNING


class TestX002UnfilledTemplate:
    @pytest.mark.parametrize(
        "title",
        [
            "Use <DB_DRIVER> for all queries",
            "Configure {your_project_name} via env vars",
            "Pin {primary_language} to the version in .python-version",
            "Run [INSERT TEST COMMAND] before each PR",
        ],
    )
    def test_detects_placeholder(self, title: str) -> None:
        assert "X002" in _codes_for(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Use asyncpg for all queries",
            "Pin python>=3.12 in pyproject.toml",
            "Run pytest before each PR",
            # Mixed-case angle bracket content is NOT flagged — likely real HTML.
            "Allow <div> tags in user input",
        ],
    )
    def test_does_not_flag_real_content(self, title: str) -> None:
        assert "X002" not in _codes_for(title)

    def test_message_names_placeholder(self) -> None:
        diags = list(antipattern.check(AgentDocument(rules=[_rule("Use <DB_DRIVER> for queries")])))
        x002 = next(d for d in diags if d.code == "X002")
        assert "<DB_DRIVER>" in x002.message


class TestX003QuestionDirective:
    @pytest.mark.parametrize(
        "title",
        [
            "Should we validate every input?",
            "Do we use camelCase or snake_case?",
            "What's the right timeout for HTTP clients?",
            "Why would we ever skip tests?",
            "Should we validate every input?   ",  # trailing whitespace tolerated
        ],
    )
    def test_detects_question(self, title: str) -> None:
        assert "X003" in _codes_for(title)

    @pytest.mark.parametrize(
        "title",
        [
            "Validate every input crossing a trust boundary",
            "Use snake_case for Python identifiers",
            "HTTP clients use a 5-second connect timeout",
        ],
    )
    def test_does_not_flag_directives(self, title: str) -> None:
        assert "X003" not in _codes_for(title)

    def test_does_not_flag_inner_question_mark(self) -> None:
        # A question mark inside the title (not trailing) shouldn't fire.
        assert "X003" not in _codes_for('Ask "What changed?" before opening a PR')


class TestCheckIntegration:
    def test_empty_agent_yields_nothing(self) -> None:
        assert list(antipattern.check(AgentDocument())) == []

    def test_multiple_x_rules_can_co_fire(self) -> None:
        # Single rule that has BOTH a TODO and a placeholder.
        rule = _rule("TODO: Use <DB_DRIVER> for queries")
        codes = [d.code for d in antipattern.check(AgentDocument(rules=[rule]))]
        assert "X001" in codes
        assert "X002" in codes

    def test_source_kwarg_accepted(self) -> None:
        list(antipattern.check(AgentDocument(rules=[_rule("Be clear")]), source="x.md"))
