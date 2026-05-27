"""Tests for the A001 vague-directive rule."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import ambiguity
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _agent_with(rules: list[Rule]) -> AgentDocument:
    return AgentDocument(rules=rules)


def _rule(title: str, sev: Severity = Severity.MUST) -> Rule:
    return Rule(
        id="X-001",
        title=title,
        severity=sev,
        position=Position(file="x.md", line=10),
    )


class TestA001Detection:
    @pytest.mark.parametrize(
        "vague_title",
        [
            "Be concise",
            "be concise",  # case-insensitive
            "BE CONCISE",
            "Be concise.",  # trailing punctuation stripped
            "Write clean code",
            "Use good naming",
            "Avoid bad practices",
            "Be careful",
            "Make it nice",
            "Keep it simple",
        ],
    )
    def test_detects_known_vague_directive(self, vague_title: str) -> None:
        diags = list(ambiguity.check(_agent_with([_rule(vague_title)])))
        assert len(diags) == 1
        assert diags[0].code == "A001"

    def test_detects_with_prefix_match(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise about error messages")])))
        assert len(diags) == 1
        assert diags[0].code == "A001"

    @pytest.mark.parametrize(
        "specific_title",
        [
            "Use type hints on every public function",
            "Public functions must be 40 lines or fewer",
            "Never commit secrets",
            "snake_case for functions, PascalCase for classes",
            "Run pytest before each PR",
        ],
    )
    def test_does_not_flag_specific_rules(self, specific_title: str) -> None:
        diags = list(ambiguity.check(_agent_with([_rule(specific_title)])))
        assert diags == []

    def test_no_rules_yields_no_diagnostics(self) -> None:
        diags = list(ambiguity.check(_agent_with([])))
        assert diags == []


class TestA001DiagnosticShape:
    def test_severity_is_warning(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise")])))
        assert diags[0].severity == DiagSeverity.WARNING

    def test_message_quotes_offending_title(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise")])))
        assert "'Be concise'" in diags[0].message

    def test_position_is_propagated(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise")])))
        pos = diags[0].position
        assert pos is not None
        assert pos.file == "x.md"
        assert pos.line == 10

    def test_suggestion_is_actionable(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise")])))
        assert diags[0].suggestion is not None
        assert "measurable" in diags[0].suggestion

    def test_doc_url_is_set(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise")])))
        assert diags[0].doc_url == "https://contextos.dev/rules/A001"
