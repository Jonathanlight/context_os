"""RAG retrieval evaluator runner — Phase 7.9.

Parallel to :class:`~contextos.eval.runner.SkillEvalRunner`: pure
orchestration, takes an :class:`EvalSuite` + a retrieval provider,
and produces an :class:`EvalRunResult`.

A case passes when **any** of its ``expected_sources`` appears in the
provider's top-k retrieval result. OR semantics over the expected
list — useful when multiple source paths could legitimately answer
the same query.
"""

from __future__ import annotations

from contextos.ast.eval import EvalSuite, RagCase
from contextos.eval.rag_providers import RagRetrievalProvider
from contextos.eval.results import EvalCaseResult, EvalRunResult


class RagEvalRunner:
    """Run an EvalSuite's rag_cases against a retrieval provider.

    Per-case errors are captured into the result (same contract as
    :class:`~contextos.eval.runner.SkillEvalRunner`) — partial reports
    beat all-or-nothing crashes.
    """

    def __init__(self, provider: RagRetrievalProvider) -> None:
        self._provider = provider

    def run(self, suite: EvalSuite) -> EvalRunResult:
        """Evaluate every ``rag_case`` in ``suite``.

        Raises ``ValueError`` when the suite is not of the rag flavor —
        catches the case where a SkillEvalRunner suite is fed to this
        runner by accident.
        """
        if suite.target != "rag":
            msg = f"RagEvalRunner requires suite.target='rag', got '{suite.target}'"
            raise ValueError(msg)

        case_results: list[EvalCaseResult] = []
        total_tokens = 0
        for case in suite.rag_cases:
            result, tokens = self._run_one(case)
            case_results.append(result)
            total_tokens += tokens

        return EvalRunResult(
            suite_project=suite.project,
            target=suite.target,
            case_results=case_results,
            total_tokens=total_tokens,
        )

    def _run_one(self, case: RagCase) -> tuple[EvalCaseResult, int]:
        """Evaluate a single case; return (result, tokens-consumed)."""
        expected = ", ".join(case.expected_sources)
        try:
            response = self._provider.retrieve(case.query, case.top_k)
        except Exception as exc:
            return (
                EvalCaseResult(
                    case_name=case.name,
                    expected=expected,
                    actual=None,
                    passed=False,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                0,
            )

        tokens = response.token_usage.total if response.token_usage else 0
        # Pass criterion: OR over the expected list.
        retrieved_set = set(response.retrieved_sources)
        passed = any(src in retrieved_set for src in case.expected_sources)
        # actual = the retrieved set, joined for human-readable rendering.
        actual = ", ".join(response.retrieved_sources) if response.retrieved_sources else None
        return (
            EvalCaseResult(
                case_name=case.name,
                expected=expected,
                actual=actual,
                passed=passed,
                tokens_used=tokens or None,
            ),
            tokens,
        )


__all__ = ["RagEvalRunner"]
