"""Eval runner that drives the Skills routing provider over a suite.

Pure orchestration — no provider-specific code lives here. The runner
takes an :class:`EvalSuite` (the cases to evaluate) and a registry of
:class:`SkillDocument` (the skills available to the model), invokes
the provider's ``route()`` for every case, compares the picked skill
to the expected one, and aggregates the results into an
:class:`EvalRunResult`.
"""

from __future__ import annotations

from contextos.ast.eval import EvalSuite, SkillCase
from contextos.ast.skill import SkillDocument
from contextos.eval.providers import SkillRoutingProvider
from contextos.eval.results import EvalCaseResult, EvalRunResult


class SkillEvalRunner:
    """Run an EvalSuite's skill_cases against a routing provider.

    Per-case errors are captured into the result rather than allowed
    to abort the run. A flaky provider — rate limit, transient
    network error — should produce a partial report the user can
    inspect, not crash the whole eval session and waste the tokens
    spent on the prior cases.
    """

    def __init__(self, provider: SkillRoutingProvider) -> None:
        self._provider = provider

    def run(
        self,
        suite: EvalSuite,
        skills: list[SkillDocument],
    ) -> EvalRunResult:
        """Evaluate every ``skill_case`` in ``suite`` against ``skills``.

        Raises ``ValueError`` when the suite is not of the skill flavor.
        The runner ignores ``rag_cases`` because those need a different
        provider type — Phase 7.9 will ship the parallel
        ``RagEvalRunner``.
        """
        if suite.target != "anthropic_skill":
            msg = f"SkillEvalRunner requires suite.target='anthropic_skill', got '{suite.target}'"
            raise ValueError(msg)

        case_results: list[EvalCaseResult] = []
        total_tokens = 0
        for case in suite.skill_cases:
            result, tokens = self._run_one(case, skills)
            case_results.append(result)
            total_tokens += tokens

        return EvalRunResult(
            suite_project=suite.project,
            target=suite.target,
            case_results=case_results,
            total_tokens=total_tokens,
        )

    def _run_one(
        self,
        case: SkillCase,
        skills: list[SkillDocument],
    ) -> tuple[EvalCaseResult, int]:
        """Evaluate a single case; return (result, tokens-consumed)."""
        try:
            response = self._provider.route(case.prompt, skills)
        except Exception as exc:
            return (
                EvalCaseResult(
                    case_name=case.name,
                    expected=case.expected_skill,
                    actual=None,
                    passed=False,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                0,
            )

        tokens = response.token_usage.total if response.token_usage else 0
        passed = response.picked_skill == case.expected_skill
        return (
            EvalCaseResult(
                case_name=case.name,
                expected=case.expected_skill,
                actual=response.picked_skill,
                passed=passed,
                tokens_used=tokens or None,
            ),
            tokens,
        )


__all__ = ["SkillEvalRunner"]
