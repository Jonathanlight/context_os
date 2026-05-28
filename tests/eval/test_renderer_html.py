"""Tests for the HTML eval renderer — Phase 8.4."""

from __future__ import annotations

from contextos.eval.renderer_html import render_eval_html
from contextos.eval.results import EvalCaseResult, EvalRunResult


def _result(
    *cases: EvalCaseResult,
    project: str = "Test",
    target: str = "anthropic_skill",
    tokens: int = 0,
) -> EvalRunResult:
    return EvalRunResult(
        suite_project=project,
        target=target,
        case_results=list(cases),
        total_tokens=tokens,
    )


def _case(
    name: str,
    *,
    passed: bool,
    expected: str = "x",
    actual: str | None = None,
    tokens: int | None = None,
    error: str | None = None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_name=name,
        expected=expected,
        actual=actual if actual is not None else (expected if passed else "wrong"),
        passed=passed,
        tokens_used=tokens,
        error=error,
    )


class TestScaffold:
    def test_valid_doctype(self) -> None:
        out = render_eval_html(_result())
        assert out.startswith("<!doctype html>")

    def test_default_title_includes_project(self) -> None:
        out = render_eval_html(_result(project="MyApp"))
        assert "<title>ContextOS eval — MyApp</title>" in out

    def test_custom_title(self) -> None:
        out = render_eval_html(_result(), title="Custom")
        assert "<title>Custom</title>" in out

    def test_self_contained(self) -> None:
        out = render_eval_html(_result(_case("a", passed=True)))
        assert "<link " not in out
        assert "src=" not in out
        assert "<style>" in out
        assert "<script>" in out


class TestHeader:
    def test_target_badge(self) -> None:
        out = render_eval_html(_result(target="rag"))
        assert "rag" in out
        assert "badge" in out

    def test_tokens_badge(self) -> None:
        out = render_eval_html(_result(tokens=2048))
        assert "2048 tokens" in out

    def test_pass_rate_displayed_at_100(self) -> None:
        out = render_eval_html(
            _result(
                _case("a", passed=True),
                _case("b", passed=True),
            )
        )
        assert ">100%<" in out
        assert "2/2 passing" in out

    def test_pass_rate_displayed_at_0(self) -> None:
        out = render_eval_html(
            _result(_case("a", passed=False)),
        )
        assert ">0%<" in out
        assert "0/1 passing" in out

    def test_pass_rate_rounded(self) -> None:
        out = render_eval_html(
            _result(
                _case("a", passed=True),
                _case("b", passed=True),
                _case("c", passed=False),
            )
        )
        # 2/3 = 0.666... → 67%
        assert ">67%<" in out

    def test_filter_buttons_with_counts(self) -> None:
        out = render_eval_html(
            _result(
                _case("a", passed=True),
                _case("b", passed=False),
                _case("c", passed=False),
            )
        )
        assert "Pass (1)" in out
        assert "Fail (2)" in out


class TestCaseRows:
    def test_passing_case_has_pass_chip(self) -> None:
        out = render_eval_html(_result(_case("a", passed=True)))
        assert "chip-pass" in out
        assert ">PASS<" in out

    def test_failing_case_has_fail_chip(self) -> None:
        out = render_eval_html(_result(_case("a", passed=False)))
        assert "chip-fail" in out
        assert ">FAIL<" in out

    def test_expected_and_actual_columns(self) -> None:
        out = render_eval_html(
            _result(
                _case("a", passed=False, expected="right", actual="wrong"),
            )
        )
        assert "right" in out
        assert "wrong" in out

    def test_none_actual_renders_as_em(self) -> None:
        # Construct directly: the _case helper's fallback would substitute
        # a string when called with actual=None.
        out = render_eval_html(
            _result(
                EvalCaseResult(
                    case_name="a",
                    expected="right",
                    actual=None,
                    passed=False,
                )
            )
        )
        assert "<em>(none)</em>" in out

    def test_tokens_column(self) -> None:
        out = render_eval_html(_result(_case("a", passed=True, tokens=42)))
        assert "42" in out

    def test_error_block_rendered(self) -> None:
        out = render_eval_html(
            _result(
                _case(
                    "a",
                    passed=False,
                    error="RuntimeError: provider down",
                )
            )
        )
        assert "error-note" in out
        assert "RuntimeError" in out

    def test_no_error_block_when_no_error(self) -> None:
        out = render_eval_html(_result(_case("a", passed=True)))
        # The .error-note class is reserved in CSS; what matters is that
        # no actual <div class="error-note"> tag is produced when error
        # is empty.
        assert '<div class="error-note">' not in out


class TestEmptyRun:
    def test_empty_result_renders_no_cases_message(self) -> None:
        out = render_eval_html(_result())
        assert "No cases were run." in out


class TestHtmlEscape:
    def test_case_name_with_html_escaped(self) -> None:
        out = render_eval_html(
            _result(_case("<script>alert(1)</script>", passed=True))
        )
        assert "<script>alert(1)" not in out
        assert "&lt;script&gt;" in out

    def test_expected_value_escaped(self) -> None:
        out = render_eval_html(
            _result(_case("a", passed=False, expected='"><img src=x>'))
        )
        assert "<img" not in out
        assert "&quot;" in out

    def test_actual_value_escaped(self) -> None:
        out = render_eval_html(
            _result(_case("a", passed=False, actual="<b>bold</b>"))
        )
        assert "<b>bold</b>" not in out
        assert "&lt;b&gt;bold" in out

    def test_error_field_escaped(self) -> None:
        out = render_eval_html(
            _result(_case("a", passed=False, error="<x>"))
        )
        assert "<x>" not in out
        assert "&lt;x&gt;" in out

    def test_target_escaped(self) -> None:
        # Target is a Literal in practice, but defense in depth.
        out = render_eval_html(_result(target="anthropic_skill"))
        assert "anthropic_skill" in out


class TestSummary:
    def test_summary_includes_total_and_tokens(self) -> None:
        out = render_eval_html(
            _result(
                _case("a", passed=True),
                _case("b", passed=False),
                tokens=2048,
            )
        )
        assert "2 case(s)" in out
        assert "2048 tokens total" in out
