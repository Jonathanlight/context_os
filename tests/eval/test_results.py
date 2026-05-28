"""Unit tests for the eval result models — Phase 7.8."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.eval.results import EvalCaseResult, EvalRunResult


def _passing(case_name: str = "case", expected: str = "x") -> EvalCaseResult:
    return EvalCaseResult(case_name=case_name, expected=expected, actual=expected, passed=True)


def _failing(case_name: str = "case", expected: str = "x") -> EvalCaseResult:
    return EvalCaseResult(case_name=case_name, expected=expected, actual="y", passed=False)


class TestEvalCaseResult:
    def test_minimal_pass(self) -> None:
        r = _passing()
        assert r.passed is True
        assert r.error is None

    def test_with_token_count(self) -> None:
        r = EvalCaseResult(
            case_name="a",
            expected="x",
            actual="x",
            passed=True,
            tokens_used=42,
        )
        assert r.tokens_used == 42

    def test_negative_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvalCaseResult(
                case_name="a",
                expected="x",
                actual="x",
                passed=True,
                tokens_used=-1,
            )

    def test_empty_case_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvalCaseResult(case_name="", expected="x", actual="x", passed=True)


class TestEvalRunResult:
    def test_empty_run_pass_rate_zero(self) -> None:
        result = EvalRunResult(suite_project="X", target="anthropic_skill")
        assert result.pass_count == 0
        assert result.fail_count == 0
        assert result.pass_rate == 0.0

    def test_pass_count_and_rate(self) -> None:
        result = EvalRunResult(
            suite_project="X",
            target="anthropic_skill",
            case_results=[_passing("a"), _passing("b"), _failing("c")],
        )
        assert result.pass_count == 2
        assert result.fail_count == 1
        assert result.pass_rate == pytest.approx(2 / 3)

    def test_total_tokens_accepts_zero(self) -> None:
        result = EvalRunResult(suite_project="X", target="rag", total_tokens=0)
        assert result.total_tokens == 0

    def test_negative_total_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvalRunResult(suite_project="X", target="rag", total_tokens=-1)
