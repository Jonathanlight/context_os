"""Tests for the eval renderer — Phase 7.10."""

from __future__ import annotations

import json

from contextos.eval.renderer import render_eval_cli, render_eval_json
from contextos.eval.results import EvalCaseResult, EvalRunResult


def _result(*cases: EvalCaseResult, total_tokens: int = 0) -> EvalRunResult:
    return EvalRunResult(
        suite_project="Test",
        target="anthropic_skill",
        case_results=list(cases),
        total_tokens=total_tokens,
    )


class TestCliRenderer:
    def test_empty_run(self) -> None:
        out = render_eval_cli(_result())
        assert "eval suite: Test" in out
        assert "pass:       0/0 (0%)" in out
        assert "no cases run" in out

    def test_all_passing(self) -> None:
        out = render_eval_cli(
            _result(
                EvalCaseResult(
                    case_name="case-a", expected="x", actual="x", passed=True,
                ),
                EvalCaseResult(
                    case_name="case-b", expected="y", actual="y", passed=True,
                ),
            )
        )
        assert "pass:       2/2 (100%)" in out
        assert "[PASS] case-a" in out
        assert "[PASS] case-b" in out
        # Passing cases should NOT include the expected/actual detail lines.
        assert "expected:" not in out
        assert "actual:" not in out

    def test_failing_case_includes_details(self) -> None:
        out = render_eval_cli(
            _result(
                EvalCaseResult(
                    case_name="case-a",
                    expected="right",
                    actual="wrong",
                    passed=False,
                )
            )
        )
        assert "[FAIL] case-a" in out
        assert "expected: right" in out
        assert "actual:   wrong" in out

    def test_failing_case_with_none_actual(self) -> None:
        out = render_eval_cli(
            _result(
                EvalCaseResult(
                    case_name="case-a",
                    expected="right",
                    actual=None,
                    passed=False,
                )
            )
        )
        assert "actual:   (none)" in out

    def test_failing_case_includes_error(self) -> None:
        out = render_eval_cli(
            _result(
                EvalCaseResult(
                    case_name="case-a",
                    expected="right",
                    actual=None,
                    passed=False,
                    error="RuntimeError: provider unavailable",
                )
            )
        )
        assert "error:    RuntimeError: provider unavailable" in out

    def test_token_total_displayed(self) -> None:
        out = render_eval_cli(
            _result(total_tokens=2048),
        )
        assert "tokens:     2048" in out


class TestJsonRenderer:
    def test_round_trip_to_python(self) -> None:
        result = _result(
            EvalCaseResult(case_name="a", expected="x", actual="x", passed=True),
        )
        rendered = render_eval_json(result)
        parsed = json.loads(rendered)
        assert parsed["suite_project"] == "Test"
        assert parsed["target"] == "anthropic_skill"
        assert parsed["case_results"][0]["case_name"] == "a"

    def test_default_indent_is_two(self) -> None:
        rendered = render_eval_json(_result())
        # An indented dump contains a newline between top-level keys.
        assert "\n  " in rendered

    def test_indent_none_yields_compact(self) -> None:
        rendered = render_eval_json(_result(), indent=None)
        assert "\n  " not in rendered
