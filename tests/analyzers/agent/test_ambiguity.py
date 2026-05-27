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
        codes = {d.code for d in diags}
        # A002 / A003 / A004 may co-fire on directives that contain subjective
        # adjectives or quantifiers; A001 must always be present.
        assert "A001" in codes

    def test_detects_with_prefix_match(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Be concise about error messages")])))
        codes = {d.code for d in diags}
        assert "A001" in codes

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


def _codes_for(title: str) -> set[str]:
    """Run every A* check on a single-rule agent and collect the codes."""
    diags = list(ambiguity.check(_agent_with([_rule(title)])))
    return {d.code for d in diags}


class TestA002SubjectiveAdjective:
    @pytest.mark.parametrize(
        "vague_title",
        [
            "Write clean code consistently",
            "Pick a proper variable name",
            "Make reasonable timeout choices",
            "Avoid ugly hacks in the parser",
            "Keep the API nice for callers",
            "Choose an appropriate abstraction",
        ],
    )
    def test_detects_subjective_adjective(self, vague_title: str) -> None:
        assert "A002" in _codes_for(vague_title)

    @pytest.mark.parametrize(
        "specific_title",
        [
            "Public functions <= 40 lines",
            "snake_case for functions and PascalCase for classes",
            "Use type hints on every public function",
            "Validate inputs at every trust boundary",
        ],
    )
    def test_does_not_flag_specific_rules(self, specific_title: str) -> None:
        assert "A002" not in _codes_for(specific_title)

    def test_match_is_whole_token(self) -> None:
        # "cleanly" should not trigger on "clean".
        assert "A002" not in _codes_for("Shut down servers cleanly on SIGTERM")

    def test_message_lists_offender(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Write clean code")])))
        a002 = next(d for d in diags if d.code == "A002")
        assert "'clean'" in a002.message

    def test_multiple_offenders_in_one_message(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Keep the code clean and elegant")])))
        a002 = next(d for d in diags if d.code == "A002")
        assert "clean" in a002.message
        assert "elegant" in a002.message


class TestA003VagueQuantifier:
    @pytest.mark.parametrize(
        "vague_title",
        [
            "Rarely share mutable state across threads",
            "Most public APIs need a docstring",
            "Sometimes prefer composition",
            "A few imports per file",
            "Several integration tests per endpoint",
        ],
    )
    def test_detects_vague_quantifier(self, vague_title: str) -> None:
        assert "A003" in _codes_for(vague_title)

    @pytest.mark.parametrize(
        "specific_title",
        [
            "Pin dependencies in pyproject.toml",
            "Every public function has a docstring",
            "Use a single import per line",
        ],
    )
    def test_does_not_flag_specific_rules(self, specific_title: str) -> None:
        assert "A003" not in _codes_for(specific_title)

    def test_match_is_whole_token(self) -> None:
        # "summary" should not match "some".
        assert "A003" not in _codes_for("Write a summary of breaking changes")
        # "frequent" should not match "frequently".
        assert "A003" not in _codes_for("Run the frequent-flyer query daily")

    def test_message_quotes_offender(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Rarely use mutable state")])))
        a003 = next(d for d in diags if d.code == "A003")
        assert "'rarely'" in a003.message


class TestA004HedgingCadence:
    @pytest.mark.parametrize(
        "hedging_title",
        [
            "Refresh credentials regularly",
            "Add tests as needed",
            "Validate inputs if necessary",
            "Refactor when appropriate",
            "Pin dependencies if possible",
            "Review the changelog from time to time",
        ],
    )
    def test_detects_hedging_phrase(self, hedging_title: str) -> None:
        assert "A004" in _codes_for(hedging_title)

    @pytest.mark.parametrize(
        "specific_title",
        [
            "Rotate credentials on every deployment",
            "Every public function has a test",
            "Validate every input at the HTTP boundary",
            "Refactor when a function exceeds 40 lines",
        ],
    )
    def test_does_not_flag_specific_rules(self, specific_title: str) -> None:
        assert "A004" not in _codes_for(specific_title)

    def test_match_is_whole_token(self) -> None:
        # "regulator" should not match "regularly".
        assert "A004" not in _codes_for("Use the rate-limiter regulator service")

    def test_message_quotes_offender(self) -> None:
        diags = list(ambiguity.check(_agent_with([_rule("Refactor when appropriate")])))
        a004 = next(d for d in diags if d.code == "A004")
        assert "'when appropriate'" in a004.message


class TestCodesIndependence:
    """A single rule can fire multiple A* codes; each one is independent."""

    def test_vague_directive_and_subjective_adjective_can_coexist(self) -> None:
        # "Write clean code" is in _VAGUE_DIRECTIVES (A001) AND contains
        # "clean" (A002). Both should fire on the same Rule.
        codes = _codes_for("Write clean code")
        assert "A001" in codes
        assert "A002" in codes

    def test_quantifier_and_hedging_are_orthogonal(self) -> None:
        # "Rarely refactor when appropriate" hits both A003 (rarely) and
        # A004 (when appropriate). They are independent signals.
        codes = _codes_for("Rarely refactor when appropriate")
        assert "A003" in codes
        assert "A004" in codes
