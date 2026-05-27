"""Tests for the K* completeness rules."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import completeness
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _agent(rules: list[Rule] | None = None) -> AgentDocument:
    return AgentDocument(rules=rules or [])


def _rule(
    *,
    severity: Severity = Severity.MUST,
    rationale: str | None = None,
    example_good: str | None = None,
    example_bad: str | None = None,
    rule_id: str = "X-001",
) -> Rule:
    return Rule(
        id=rule_id,
        title="t",
        severity=severity,
        rationale=rationale,
        example_good=example_good,
        example_bad=example_bad,
        position=Position(file="x.md", line=10),
    )


def _codes(agent: AgentDocument) -> list[str]:
    return [d.code for d in completeness.check(agent)]


class TestK001NoRules:
    def test_fires_on_empty_rules(self) -> None:
        assert "K001" in _codes(_agent([]))

    def test_silent_when_any_rule_present(self) -> None:
        assert "K001" not in _codes(_agent([_rule()]))

    def test_diagnostic_has_no_position(self) -> None:
        # K001 is a doc-level diagnostic; no specific line to point at.
        diags = list(completeness.check(_agent([])))
        k001 = next(d for d in diags if d.code == "K001")
        assert k001.position is None

    def test_severity_is_warning(self) -> None:
        diags = list(completeness.check(_agent([])))
        k001 = next(d for d in diags if d.code == "K001")
        assert k001.severity == DiagSeverity.WARNING


class TestK002MustWithoutRationale:
    def test_fires_on_must_without_rationale(self) -> None:
        assert "K002" in _codes(_agent([_rule(severity=Severity.MUST)]))

    def test_silent_when_rationale_present(self) -> None:
        rule = _rule(severity=Severity.MUST, rationale="prevents the bad thing")
        assert "K002" not in _codes(_agent([rule]))

    def test_treats_whitespace_only_rationale_as_missing(self) -> None:
        rule = _rule(severity=Severity.MUST, rationale="   \n  ")
        assert "K002" in _codes(_agent([rule]))

    @pytest.mark.parametrize("sev", [Severity.SHOULD, Severity.MAY])
    def test_silent_for_non_must_severities(self, sev: Severity) -> None:
        rule = _rule(severity=sev)
        assert "K002" not in _codes(_agent([rule]))

    def test_message_references_rule_id(self) -> None:
        rule = _rule(severity=Severity.MUST, rule_id="SEC-042")
        diags = list(completeness.check(_agent([rule])))
        k002 = next(d for d in diags if d.code == "K002")
        assert "'SEC-042'" in k002.message


class TestK003MustWithoutExamples:
    def test_fires_on_must_without_either_example(self) -> None:
        assert "K003" in _codes(_agent([_rule(severity=Severity.MUST)]))

    def test_silent_when_example_good_present(self) -> None:
        rule = _rule(severity=Severity.MUST, example_good="snake_case")
        assert "K003" not in _codes(_agent([rule]))

    def test_silent_when_example_bad_present(self) -> None:
        rule = _rule(severity=Severity.MUST, example_bad="camelCase")
        assert "K003" not in _codes(_agent([rule]))

    def test_silent_when_both_examples_present(self) -> None:
        rule = _rule(
            severity=Severity.MUST,
            example_good="snake_case",
            example_bad="camelCase",
        )
        assert "K003" not in _codes(_agent([rule]))

    @pytest.mark.parametrize("sev", [Severity.SHOULD, Severity.MAY])
    def test_silent_for_non_must_severities(self, sev: Severity) -> None:
        rule = _rule(severity=sev)
        assert "K003" not in _codes(_agent([rule]))

    def test_severity_is_info(self) -> None:
        # K003 is gentler than K002.
        diags = list(completeness.check(_agent([_rule(severity=Severity.MUST)])))
        k003 = next(d for d in diags if d.code == "K003")
        assert k003.severity == DiagSeverity.INFO

    def test_treats_whitespace_only_example_as_missing(self) -> None:
        rule = _rule(severity=Severity.MUST, example_good="   ")
        assert "K003" in _codes(_agent([rule]))


class TestK002K003Coexistence:
    """K002 and K003 are independent — a must-rule with neither fires both."""

    def test_both_fire_on_bare_must_rule(self) -> None:
        codes = _codes(_agent([_rule(severity=Severity.MUST)]))
        assert "K002" in codes
        assert "K003" in codes

    def test_only_k002_when_examples_present_but_no_rationale(self) -> None:
        rule = _rule(severity=Severity.MUST, example_good="snake_case")
        codes = _codes(_agent([rule]))
        assert "K002" in codes
        assert "K003" not in codes

    def test_only_k003_when_rationale_present_but_no_examples(self) -> None:
        rule = _rule(severity=Severity.MUST, rationale="why")
        codes = _codes(_agent([rule]))
        assert "K003" in codes
        assert "K002" not in codes


class TestK001IntegrationWithRuleChecks:
    """K001 fires once at the document level even when rules-level checks would have fired too."""

    def test_empty_rules_yields_only_k001(self) -> None:
        codes = _codes(_agent([]))
        # K002 / K003 cannot fire — there's nothing to check.
        assert codes == ["K001"]


class TestSourceKwarg:
    def test_accepts_source_kwarg(self) -> None:
        # Same contract as the other category modules.
        list(completeness.check(_agent([_rule()]), source="x.md"))
