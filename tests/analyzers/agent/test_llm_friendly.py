"""Tests for the F* LLM-friendliness rules."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import llm_friendly
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _agent_with(rules: list[Rule]) -> AgentDocument:
    return AgentDocument(rules=rules)


def _rule(
    title: str,
    rule_id: str = "X-001",
    sev: Severity = Severity.MUST,
) -> Rule:
    return Rule(
        id=rule_id,
        title=title,
        severity=sev,
        position=Position(file="x.md", line=10),
    )


def _codes_for(rules: list[Rule]) -> list[str]:
    return [d.code for d in llm_friendly.check(_agent_with(rules))]


class TestF001ExcessiveCaps:
    @pytest.mark.parametrize(
        "shouty_title",
        [
            "MUST USE TYPE HINTS ON EVERY PUBLIC FUNCTION",
            "NEVER COMMIT API KEYS OR DATABASE PASSWORDS",
            "ALWAYS VALIDATE INPUTS AT EVERY TRUST BOUNDARY",
            "RUN THE FULL TEST SUITE BEFORE EACH PULL REQUEST",
        ],
    )
    def test_detects_all_caps(self, shouty_title: str) -> None:
        assert "F001" in _codes_for([_rule(shouty_title)])

    @pytest.mark.parametrize(
        "normal_title",
        [
            "Use type hints on every public function",
            "Use HTTPS and HTTP/2 for API endpoints",
            "Reject requests without an OAuth2 token",
            "Validate JSON payloads against the schema",
        ],
    )
    def test_does_not_flag_normal_case(self, normal_title: str) -> None:
        assert "F001" not in _codes_for([_rule(normal_title)])

    def test_short_caps_title_is_not_flagged(self) -> None:
        # "USE HTTPS" is only 8 letters — below the 15-letter minimum.
        assert "F001" not in _codes_for([_rule("USE HTTPS")])

    def test_message_includes_ratio(self) -> None:
        diags = list(llm_friendly.check(_agent_with([_rule("MUST USE TYPE HINTS NOW")])))
        f001 = next(d for d in diags if d.code == "F001")
        # Ratio rendered as "letters_uppercase/letters_total".
        assert "/" in f001.message

    def test_severity_is_warning(self) -> None:
        diags = list(llm_friendly.check(_agent_with([_rule("MUST USE TYPE HINTS NOW")])))
        f001 = next(d for d in diags if d.code == "F001")
        assert f001.severity == DiagSeverity.WARNING


class TestF002TitleTooLong:
    def test_flags_title_over_120_chars(self) -> None:
        long_title = "x " * 70  # 140 chars
        codes = _codes_for([_rule(long_title.strip())])
        assert "F002" in codes

    def test_does_not_flag_short_title(self) -> None:
        assert "F002" not in _codes_for([_rule("Use type hints")])

    def test_boundary_at_120_chars(self) -> None:
        title_120 = "a" * 120
        title_121 = "a" * 121
        assert "F002" not in _codes_for([_rule(title_120)])
        assert "F002" in _codes_for([_rule(title_121)])

    def test_message_includes_actual_length(self) -> None:
        title = "a" * 130
        diags = list(llm_friendly.check(_agent_with([_rule(title)])))
        f002 = next(d for d in diags if d.code == "F002")
        assert "130" in f002.message
        assert "120" in f002.message

    def test_suggestion_mentions_structured_fields(self) -> None:
        diags = list(llm_friendly.check(_agent_with([_rule("a" * 130)])))
        f002 = next(d for d in diags if d.code == "F002")
        assert f002.suggestion is not None
        assert "rationale" in f002.suggestion or "detail" in f002.suggestion


class TestF003DuplicateRule:
    def test_detects_identical_titles(self) -> None:
        rules = [
            _rule("Use type hints", rule_id="A-001"),
            _rule("Use type hints", rule_id="A-002"),
        ]
        diags = list(llm_friendly.check(_agent_with(rules)))
        f003 = [d for d in diags if d.code == "F003"]
        assert len(f003) == 1
        assert "A-001" in f003[0].message

    def test_detects_titles_differing_only_by_punctuation(self) -> None:
        rules = [
            _rule("Use type hints.", rule_id="A-001"),
            _rule("Use type hints", rule_id="A-002"),
        ]
        diags = list(llm_friendly.check(_agent_with(rules)))
        assert any(d.code == "F003" for d in diags)

    def test_detects_titles_differing_only_by_case(self) -> None:
        rules = [
            _rule("Use Type Hints", rule_id="A-001"),
            _rule("use type hints", rule_id="A-002"),
        ]
        diags = list(llm_friendly.check(_agent_with(rules)))
        assert any(d.code == "F003" for d in diags)

    def test_first_occurrence_is_canonical(self) -> None:
        rules = [
            _rule("Use type hints", rule_id="A-001"),
            _rule("Use type hints", rule_id="A-002"),
            _rule("Use type hints", rule_id="A-003"),
        ]
        diags = list(llm_friendly.check(_agent_with(rules)))
        f003 = [d for d in diags if d.code == "F003"]
        # First rule is canonical; second and third both flagged with A-001.
        assert len(f003) == 2
        assert all("A-001" in d.message for d in f003)

    def test_no_duplicates_yields_no_f003(self) -> None:
        rules = [
            _rule("Use type hints", rule_id="A-001"),
            _rule("Pin dependencies", rule_id="A-002"),
        ]
        codes = _codes_for(rules)
        assert "F003" not in codes

    def test_suggestion_references_canonical_id(self) -> None:
        rules = [
            _rule("Use type hints", rule_id="STYLE-001"),
            _rule("Use type hints", rule_id="STYLE-007"),
        ]
        diags = list(llm_friendly.check(_agent_with(rules)))
        f003 = next(d for d in diags if d.code == "F003")
        assert f003.suggestion is not None
        assert "STYLE-001" in f003.suggestion


class TestCheckIntegration:
    def test_empty_agent_yields_nothing(self) -> None:
        assert list(llm_friendly.check(AgentDocument())) == []

    def test_multiple_f_rules_can_co_fire(self) -> None:
        # One rule that is BOTH all caps (>=15 letters) AND too long
        # (>120 chars).
        long_caps_title = "MUST DO X FOR EVERY PUBLIC FUNCTION " * 5
        codes = _codes_for([_rule(long_caps_title.strip())])
        assert "F001" in codes
        assert "F002" in codes

    def test_source_kwarg_is_accepted(self) -> None:
        # Same contract as the other analyzers.
        list(llm_friendly.check(_agent_with([_rule("MUST DO X")]), source="x.md"))
