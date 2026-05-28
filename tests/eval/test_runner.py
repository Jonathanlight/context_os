"""Tests for the SkillEvalRunner — Phase 7.8."""

from __future__ import annotations

import pytest

from contextos.ast.eval import EvalSuite, RagCase, SkillCase
from contextos.ast.skill import SkillDocument
from contextos.eval.providers import MockSkillProvider
from contextos.eval.runner import SkillEvalRunner


def _skill(name: str) -> SkillDocument:
    return SkillDocument(
        name=name,
        title=f"Skill {name}",
        description=(f"Triggers when the user wants to run {name} or invoke the {name} pipeline."),
    )


def _case(name: str, prompt: str, expected: str) -> SkillCase:
    return SkillCase(name=name, prompt=prompt, expected_skill=expected)


def _suite(cases: list[SkillCase]) -> EvalSuite:
    return EvalSuite(project="Test", target="anthropic_skill", skill_cases=cases)


class TestRunnerHappyPath:
    def test_all_passing(self) -> None:
        provider = MockSkillProvider(
            {
                "do pdf": "pdf-extract",
                "do invoice": "invoice-parser",
            }
        )
        suite = _suite(
            [
                _case("a", "do pdf", "pdf-extract"),
                _case("b", "do invoice", "invoice-parser"),
            ]
        )
        runner = SkillEvalRunner(provider)
        result = runner.run(suite, [_skill("pdf-extract"), _skill("invoice-parser")])
        assert result.pass_count == 2
        assert result.fail_count == 0
        assert result.pass_rate == 1.0
        assert result.suite_project == "Test"
        assert result.target == "anthropic_skill"

    def test_all_failing(self) -> None:
        provider = MockSkillProvider({}, default="wrong-skill")
        suite = _suite([_case("a", "x", "right-skill")])
        result = SkillEvalRunner(provider).run(suite, [_skill("right-skill")])
        assert result.pass_count == 0
        assert result.fail_count == 1
        assert result.pass_rate == 0.0
        assert result.case_results[0].actual == "wrong-skill"

    def test_mixed_results(self) -> None:
        provider = MockSkillProvider(
            {
                "good": "pdf",
                "bad": "other",
            }
        )
        suite = _suite(
            [
                _case("a", "good", "pdf"),
                _case("b", "bad", "pdf"),
            ]
        )
        result = SkillEvalRunner(provider).run(suite, [_skill("pdf"), _skill("other")])
        assert result.pass_count == 1
        assert result.fail_count == 1


class TestRunnerErrorHandling:
    def test_provider_error_captured_as_case_failure(self) -> None:
        provider = MockSkillProvider({}, error_for=frozenset({"crash"}))
        suite = _suite([_case("a", "crash", "anything")])
        result = SkillEvalRunner(provider).run(suite, [_skill("anything")])
        assert result.pass_count == 0
        assert result.fail_count == 1
        case_result = result.case_results[0]
        assert case_result.passed is False
        assert case_result.actual is None
        assert case_result.error is not None
        assert "RuntimeError" in case_result.error

    def test_error_does_not_abort_run(self) -> None:
        provider = MockSkillProvider(
            {"good": "pdf"},
            error_for=frozenset({"crash"}),
        )
        suite = _suite(
            [
                _case("a", "good", "pdf"),
                _case("b", "crash", "anything"),
                _case("c", "good", "pdf"),
            ]
        )
        result = SkillEvalRunner(provider).run(suite, [_skill("pdf")])
        assert len(result.case_results) == 3
        assert result.pass_count == 2
        assert result.fail_count == 1


class TestRunnerInvariants:
    def test_rejects_wrong_target_suite(self) -> None:
        suite = EvalSuite(
            project="X",
            target="rag",
            rag_cases=[
                RagCase(name="r", query="q", expected_sources=["s.md"]),
            ],
        )
        with pytest.raises(ValueError, match=r"requires suite\.target='anthropic_skill'"):
            SkillEvalRunner(MockSkillProvider({})).run(suite, [])

    def test_empty_suite_returns_empty_results(self) -> None:
        suite = _suite([])
        result = SkillEvalRunner(MockSkillProvider({})).run(suite, [])
        assert result.case_results == []
        assert result.pass_count == 0
        assert result.pass_rate == 0.0

    def test_total_tokens_is_zero_for_mock(self) -> None:
        # The mock provider reports zero tokens; the runner sums them.
        provider = MockSkillProvider({"a": "b"})
        suite = _suite([_case("a", "a", "b"), _case("c", "a", "b")])
        result = SkillEvalRunner(provider).run(suite, [_skill("b")])
        assert result.total_tokens == 0
