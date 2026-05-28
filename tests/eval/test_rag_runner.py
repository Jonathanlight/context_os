"""Tests for the RagEvalRunner — Phase 7.9."""

from __future__ import annotations

import pytest

from contextos.ast.eval import EvalSuite, RagCase, SkillCase
from contextos.eval.rag_providers import MockRagProvider
from contextos.eval.rag_runner import RagEvalRunner


def _case(
    name: str,
    query: str,
    expected: list[str],
    top_k: int = 5,
) -> RagCase:
    return RagCase(
        name=name,
        query=query,
        expected_sources=expected,
        top_k=top_k,
    )


def _suite(cases: list[RagCase]) -> EvalSuite:
    return EvalSuite(project="Test", target="rag", rag_cases=cases)


class TestRunnerHappyPath:
    def test_expected_in_retrieved_passes(self) -> None:
        provider = MockRagProvider(
            {"vacation policy?": ["docs/policies/vacation.md", "docs/handbook.md"]}
        )
        suite = _suite(
            [_case("a", "vacation policy?", ["docs/policies/vacation.md"])]
        )
        result = RagEvalRunner(provider).run(suite)
        assert result.pass_count == 1
        assert result.fail_count == 0

    def test_expected_not_in_retrieved_fails(self) -> None:
        provider = MockRagProvider(
            {"q": ["docs/wrong.md", "docs/another-wrong.md"]}
        )
        suite = _suite([_case("a", "q", ["docs/right.md"])])
        result = RagEvalRunner(provider).run(suite)
        assert result.pass_count == 0
        assert result.fail_count == 1

    def test_or_semantics_on_expected_list(self) -> None:
        # Any one match counts as a pass.
        provider = MockRagProvider({"q": ["docs/b.md"]})
        suite = _suite(
            [_case("a", "q", ["docs/a.md", "docs/b.md", "docs/c.md"])]
        )
        result = RagEvalRunner(provider).run(suite)
        assert result.pass_count == 1

    def test_top_k_respected(self) -> None:
        # Provider returns 5 sources but top_k=2 truncates them.
        provider = MockRagProvider({"q": ["a.md", "b.md", "c.md", "d.md", "e.md"]})
        # Expected source is at position 3 (top-3 = a/b/c). With top_k=2
        # the expected d.md is NOT in the retrieval set → fail.
        suite = _suite([_case("a", "q", ["d.md"], top_k=2)])
        result = RagEvalRunner(provider).run(suite)
        assert result.pass_count == 0


class TestErrorHandling:
    def test_provider_error_captured_as_failure(self) -> None:
        provider = MockRagProvider({}, error_for=frozenset({"crash"}))
        suite = _suite([_case("a", "crash", ["doesnt.md"])])
        result = RagEvalRunner(provider).run(suite)
        assert result.pass_count == 0
        case_result = result.case_results[0]
        assert case_result.passed is False
        assert case_result.error is not None
        assert "RuntimeError" in case_result.error
        assert case_result.actual is None

    def test_error_does_not_abort_run(self) -> None:
        provider = MockRagProvider(
            {"good": ["right.md"]},
            error_for=frozenset({"crash"}),
        )
        suite = _suite(
            [
                _case("a", "good", ["right.md"]),
                _case("b", "crash", ["x.md"]),
                _case("c", "good", ["right.md"]),
            ]
        )
        result = RagEvalRunner(provider).run(suite)
        assert len(result.case_results) == 3
        assert result.pass_count == 2


class TestInvariants:
    def test_rejects_skill_target_suite(self) -> None:
        suite = EvalSuite(
            project="X",
            target="anthropic_skill",
            skill_cases=[SkillCase(name="x", prompt="y", expected_skill="z")],
        )
        with pytest.raises(ValueError, match=r"requires suite\.target='rag'"):
            RagEvalRunner(MockRagProvider({})).run(suite)

    def test_empty_suite_returns_empty_results(self) -> None:
        suite = _suite([])
        result = RagEvalRunner(MockRagProvider({})).run(suite)
        assert result.case_results == []
        assert result.pass_count == 0

    def test_actual_field_lists_retrieved_sources(self) -> None:
        provider = MockRagProvider({"q": ["a.md", "b.md"]})
        suite = _suite([_case("a", "q", ["c.md"])])
        result = RagEvalRunner(provider).run(suite)
        # actual is the joined retrieved set for human-readable rendering.
        assert result.case_results[0].actual == "a.md, b.md"

    def test_no_retrieval_actual_is_none(self) -> None:
        provider = MockRagProvider({})  # empty default
        suite = _suite([_case("a", "q", ["x.md"])])
        result = RagEvalRunner(provider).run(suite)
        assert result.case_results[0].actual is None
