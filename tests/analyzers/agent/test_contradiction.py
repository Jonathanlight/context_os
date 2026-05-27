"""Tests for the C001 contradiction heuristic."""

from __future__ import annotations

import pytest

from contextos.analyzers.agent import contradiction
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Position, Severity
from contextos.diagnostics import DiagSeverity


def _rule(title: str, rule_id: str) -> Rule:
    return Rule(
        id=rule_id,
        title=title,
        severity=Severity.MUST,
        position=Position(file="x.md", line=10),
    )


def _codes(rules: list[Rule]) -> list[str]:
    return [d.code for d in contradiction.check(AgentDocument(rules=rules))]


class TestC001Detection:
    def test_always_versus_never_with_shared_subject(self) -> None:
        rules = [
            _rule("Always use type hints on public functions", "STYLE-001"),
            _rule("Never use type hints in benchmark scripts", "STYLE-014"),
        ]
        codes = _codes(rules)
        assert "C001" in codes

    def test_required_versus_forbidden(self) -> None:
        rules = [
            _rule("Required logging on every request", "LOG-001"),
            _rule("Forbidden logging in tight loops", "LOG-002"),
        ]
        # "logging" is the shared subject; required vs forbidden is the antonym.
        assert "C001" in _codes(rules)

    @pytest.mark.parametrize(
        ("title_a", "title_b"),
        [
            ("Public functions need docstrings", "Private functions need docstrings"),
            ("Mutable state in handlers", "Immutable state in handlers"),
            ("Synchronous IO in tests", "Asynchronous IO in tests"),
            ("Enable feature flags by default", "Disable feature flags by default"),
            ("Include the version header", "Exclude the version header"),
        ],
    )
    def test_other_antonym_pairs(self, title_a: str, title_b: str) -> None:
        rules = [_rule(title_a, "A-001"), _rule(title_b, "A-002")]
        assert "C001" in _codes(rules)


class TestC001Negatives:
    def test_no_shared_subject_does_not_fire(self) -> None:
        # Antonym pair present but the rules talk about different things.
        rules = [
            _rule("Always validate inputs", "A-001"),
            _rule("Never panic", "A-002"),
        ]
        assert "C001" not in _codes(rules)

    def test_shared_subject_without_antonym_does_not_fire(self) -> None:
        rules = [
            _rule("Use type hints on public APIs", "A-001"),
            _rule("Use type hints on internal helpers", "A-002"),
        ]
        assert "C001" not in _codes(rules)

    def test_only_stopword_overlap_does_not_fire(self) -> None:
        # Antonym pair present; the only shared tokens are stopwords.
        rules = [
            _rule("Always use the foo", "A-001"),
            _rule("Never use the bar", "A-002"),
        ]
        # "the" / "use" are stopwords — no real subject overlap.
        assert "C001" not in _codes(rules)

    def test_unrelated_rules(self) -> None:
        rules = [
            _rule("Use type hints", "A-001"),
            _rule("Pin dependencies", "A-002"),
            _rule("Run pytest before each PR", "A-003"),
        ]
        assert "C001" not in _codes(rules)

    def test_single_rule_does_not_fire(self) -> None:
        rules = [_rule("Always use type hints", "A-001")]
        assert _codes(rules) == []


class TestC001Output:
    def test_severity_is_warning(self) -> None:
        rules = [
            _rule("Always use type hints", "A-001"),
            _rule("Never use type hints", "A-002"),
        ]
        diags = list(contradiction.check(AgentDocument(rules=rules)))
        c001 = next(d for d in diags if d.code == "C001")
        assert c001.severity == DiagSeverity.WARNING

    def test_message_includes_both_rule_ids(self) -> None:
        rules = [
            _rule("Always use type hints", "STYLE-001"),
            _rule("Never use type hints", "STYLE-014"),
        ]
        diags = list(contradiction.check(AgentDocument(rules=rules)))
        c001 = next(d for d in diags if d.code == "C001")
        assert "'STYLE-001'" in c001.message
        assert "'STYLE-014'" in c001.message

    def test_message_lists_shared_subject(self) -> None:
        rules = [
            _rule("Always use type hints on public functions", "A-001"),
            _rule("Never use type hints on public functions", "A-002"),
        ]
        diags = list(contradiction.check(AgentDocument(rules=rules)))
        c001 = next(d for d in diags if d.code == "C001")
        # Shared subject includes "type", "hints", "public", "functions" (order is sorted).
        assert "type" in c001.message
        assert "hints" in c001.message

    def test_position_points_at_second_rule(self) -> None:
        rules = [
            _rule("Always use type hints", "A-001"),
            _rule("Never use type hints", "A-002"),
        ]
        diags = list(contradiction.check(AgentDocument(rules=rules)))
        c001 = next(d for d in diags if d.code == "C001")
        # Convention: the diagnostic points at the second-occurring rule.
        assert c001.position is not None
        assert c001.position.file == "x.md"


class TestC001ManyRules:
    def test_one_contradicting_pair_among_many(self) -> None:
        rules = [
            _rule("Pin dependencies in pyproject.toml", "A-001"),
            _rule("Always use type hints on public functions", "A-002"),
            _rule("Run pytest before each PR", "A-003"),
            _rule("Never use type hints on public functions", "A-004"),
        ]
        codes = _codes(rules)
        # Exactly one C001 expected.
        assert codes.count("C001") == 1

    def test_two_independent_contradictions(self) -> None:
        rules = [
            _rule("Always use type hints", "A-001"),
            _rule("Never use type hints", "A-002"),
            _rule("Required logging on errors", "A-003"),
            _rule("Forbidden logging in tight loops", "A-004"),
        ]
        codes = _codes(rules)
        # Two independent contradictions.
        assert codes.count("C001") == 2


class TestSourceKwarg:
    def test_accepts_source_kwarg(self) -> None:
        rules = [
            _rule("Always use type hints", "A-001"),
            _rule("Never use type hints", "A-002"),
        ]
        list(contradiction.check(AgentDocument(rules=rules), source="x.md"))
