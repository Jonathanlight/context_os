"""Unit tests for the eval diff — Phase 7.11."""

from __future__ import annotations

import json

from contextos.eval.diff import (
    compute_eval_diff,
    render_diff_cli,
    render_diff_json,
)
from contextos.eval.results import EvalCaseResult, EvalRunResult


def _case(
    name: str,
    *,
    passed: bool,
    expected: str = "x",
    actual: str | None = None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_name=name,
        expected=expected,
        actual=actual if actual is not None else (expected if passed else "wrong"),
        passed=passed,
    )


def _run(*cases: EvalCaseResult, total_tokens: int = 0) -> EvalRunResult:
    return EvalRunResult(
        suite_project="Test",
        target="anthropic_skill",
        case_results=list(cases),
        total_tokens=total_tokens,
    )


class TestNoChanges:
    def test_identical_runs_yield_empty_buckets(self) -> None:
        baseline = _run(_case("a", passed=True), _case("b", passed=False))
        current = _run(_case("a", passed=True), _case("b", passed=False))
        diff = compute_eval_diff(baseline, current)
        assert diff.regressions == []
        assert diff.improvements == []
        assert diff.new_failures == []
        assert diff.new_passes == []
        assert diff.removed_cases == []
        assert not diff.has_regressions()
        assert not diff.has_new_failures()


class TestRegression:
    def test_pass_to_fail_classified_as_regression(self) -> None:
        baseline = _run(_case("a", passed=True))
        current = _run(_case("a", passed=False))
        diff = compute_eval_diff(baseline, current)
        assert len(diff.regressions) == 1
        assert diff.regressions[0].case_name == "a"
        assert diff.regressions[0].kind == "regression"
        assert diff.regressions[0].baseline_passed is True
        assert diff.regressions[0].current_passed is False
        assert diff.has_regressions()


class TestImprovement:
    def test_fail_to_pass_classified_as_improvement(self) -> None:
        baseline = _run(_case("a", passed=False))
        current = _run(_case("a", passed=True))
        diff = compute_eval_diff(baseline, current)
        assert len(diff.improvements) == 1
        assert diff.improvements[0].kind == "improvement"
        assert not diff.has_regressions()


class TestNewCases:
    def test_new_passing_case(self) -> None:
        baseline = _run()
        current = _run(_case("a", passed=True))
        diff = compute_eval_diff(baseline, current)
        assert len(diff.new_passes) == 1
        assert diff.new_passes[0].kind == "new_pass"
        assert diff.new_passes[0].baseline_passed is None

    def test_new_failing_case(self) -> None:
        baseline = _run()
        current = _run(_case("a", passed=False))
        diff = compute_eval_diff(baseline, current)
        assert len(diff.new_failures) == 1
        assert diff.new_failures[0].kind == "new_failure"
        assert diff.has_new_failures()
        # New failures don't count as regressions — the gate is separate.
        assert not diff.has_regressions()


class TestRemovedCases:
    def test_case_in_baseline_not_in_current_is_removed(self) -> None:
        baseline = _run(_case("a", passed=True), _case("b", passed=True))
        current = _run(_case("a", passed=True))
        diff = compute_eval_diff(baseline, current)
        assert len(diff.removed_cases) == 1
        assert diff.removed_cases[0].case_name == "b"
        assert diff.removed_cases[0].kind == "removed"
        assert diff.removed_cases[0].current_passed is None


class TestMixedTransitions:
    def test_all_buckets_populated(self) -> None:
        baseline = _run(
            _case("regress", passed=True),  # will fail in current
            _case("improve", passed=False),  # will pass in current
            _case("stay-pass", passed=True),  # unchanged
            _case("stay-fail", passed=False),  # unchanged
            _case("removed", passed=True),  # not in current
        )
        current = _run(
            _case("regress", passed=False),
            _case("improve", passed=True),
            _case("stay-pass", passed=True),
            _case("stay-fail", passed=False),
            _case("new-pass", passed=True),
            _case("new-fail", passed=False),
        )
        diff = compute_eval_diff(baseline, current)
        assert len(diff.regressions) == 1
        assert diff.regressions[0].case_name == "regress"
        assert len(diff.improvements) == 1
        assert diff.improvements[0].case_name == "improve"
        assert len(diff.new_passes) == 1
        assert diff.new_passes[0].case_name == "new-pass"
        assert len(diff.new_failures) == 1
        assert diff.new_failures[0].case_name == "new-fail"
        assert len(diff.removed_cases) == 1
        assert diff.removed_cases[0].case_name == "removed"


class TestTokenDelta:
    def test_positive_delta(self) -> None:
        baseline = _run(_case("a", passed=True), total_tokens=100)
        current = _run(_case("a", passed=True), total_tokens=150)
        diff = compute_eval_diff(baseline, current)
        assert diff.token_delta == 50

    def test_negative_delta(self) -> None:
        baseline = _run(_case("a", passed=True), total_tokens=200)
        current = _run(_case("a", passed=True), total_tokens=80)
        diff = compute_eval_diff(baseline, current)
        assert diff.token_delta == -120


class TestRendering:
    def test_cli_no_changes(self) -> None:
        baseline = _run(_case("a", passed=True))
        current = _run(_case("a", passed=True))
        diff = compute_eval_diff(baseline, current)
        out = render_diff_cli(diff)
        assert "no changes vs baseline" in out
        assert "Regressions" not in out

    def test_cli_with_regression(self) -> None:
        baseline = _run(_case("a", passed=True))
        current = _run(_case("a", passed=False))
        diff = compute_eval_diff(baseline, current)
        out = render_diff_cli(diff)
        assert "Regressions" in out
        assert "- a" in out

    def test_cli_token_delta_signed(self) -> None:
        baseline = _run(_case("a", passed=True), total_tokens=100)
        current = _run(_case("a", passed=True), total_tokens=150)
        diff = compute_eval_diff(baseline, current)
        out = render_diff_cli(diff)
        assert "+50" in out

    def test_cli_zero_token_delta(self) -> None:
        baseline = _run(_case("a", passed=True))
        current = _run(_case("a", passed=True))
        diff = compute_eval_diff(baseline, current)
        out = render_diff_cli(diff)
        assert "0 vs baseline" in out

    def test_json_round_trip(self) -> None:
        baseline = _run(_case("a", passed=True))
        current = _run(_case("a", passed=False))
        diff = compute_eval_diff(baseline, current)
        rendered = render_diff_json(diff)
        parsed = json.loads(rendered)
        assert parsed["suite_project"] == "Test"
        assert len(parsed["regressions"]) == 1
        assert parsed["regressions"][0]["kind"] == "regression"
