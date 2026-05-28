"""Pydantic models for evaluation results — Phase 7.8.

Decoupled from the AST (``contextos.ast.eval``) because results carry
ephemeral data — token counts, raw model output, the picked-but-not-
expected skill name. The AST stays a pure description of *what to
evaluate*; results describe *what happened when we ran it*.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvalCaseResult(BaseModel):
    """Outcome of evaluating a single :class:`SkillCase` or :class:`RagCase`."""

    model_config = ConfigDict(extra="forbid")

    case_name: str = Field(min_length=1)
    expected: str = Field(
        min_length=1,
        description=(
            "What we expected (skill slug for SkillCase, comma-joined "
            "expected_sources for RagCase). Stringified for uniform "
            "rendering across both families."
        ),
    )
    actual: str | None = Field(
        default=None,
        description=(
            "What the provider returned. ``None`` means the model "
            "declined to route (skill cases) or retrieval returned no "
            "matches (rag cases)."
        ),
    )
    passed: bool
    tokens_used: int | None = Field(default=None, ge=0)
    error: str | None = Field(
        default=None,
        description=(
            "Stringified exception when the provider raised — kept so "
            "the JSON report distinguishes 'failed routing' from "
            "'provider crashed'."
        ),
    )


class EvalRunResult(BaseModel):
    """Aggregate report for one ``ctx eval`` invocation."""

    model_config = ConfigDict(extra="forbid")

    suite_project: str
    target: str
    case_results: list[EvalCaseResult] = Field(default_factory=list)
    total_tokens: int = Field(default=0, ge=0)

    @property
    def pass_count(self) -> int:
        """Number of cases that passed."""
        return sum(1 for r in self.case_results if r.passed)

    @property
    def fail_count(self) -> int:
        """Number of cases that failed (including provider errors)."""
        return sum(1 for r in self.case_results if not r.passed)

    @property
    def pass_rate(self) -> float:
        """Fraction of cases that passed, 0..1. Empty suite returns 0."""
        if not self.case_results:
            return 0.0
        return self.pass_count / len(self.case_results)


__all__ = ["EvalCaseResult", "EvalRunResult"]
