"""Eval result diff for CI regression detection — Phase 7.11.

Compares a baseline :class:`EvalRunResult` (typically committed
alongside the suite) to a fresh run's result and classifies every
case into one of five buckets:

- **regression** — case passed in baseline, fails now (the only
  bucket that should break CI by default).
- **improvement** — case failed in baseline, passes now.
- **new_failure** — case is new in the current run and failing.
- **new_pass** — case is new in the current run and passing.
- **removed** — case was in baseline but not in the current run.

Unchanged passes and unchanged failures are not enumerated — they're
counted in the totals but not listed per-case. The interesting
signal is the transitions.

The renderer mirrors :mod:`contextos.eval.renderer`: CLI text for
human inspection, JSON for downstream tooling.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contextos.eval.results import EvalCaseResult, EvalRunResult

ChangeKind = Literal["regression", "improvement", "new_failure", "new_pass", "removed"]


class CaseChange(BaseModel):
    """One case transitioned between baseline and current.

    The bucket is determined at diff construction time and stored
    on the model so a JSON consumer can filter without re-running
    the classification logic.
    """

    model_config = ConfigDict(extra="forbid")

    case_name: str = Field(min_length=1)
    kind: ChangeKind
    baseline_passed: bool | None = Field(
        default=None,
        description="True/False when the case was in baseline; None when new.",
    )
    current_passed: bool | None = Field(
        default=None,
        description="True/False when the case is in current; None when removed.",
    )
    expected: str | None = None
    baseline_actual: str | None = None
    current_actual: str | None = None


class EvalDiff(BaseModel):
    """Aggregate comparison between baseline and current runs."""

    model_config = ConfigDict(extra="forbid")

    suite_project: str
    baseline_total: int = Field(ge=0)
    current_total: int = Field(ge=0)
    baseline_pass_count: int = Field(ge=0)
    current_pass_count: int = Field(ge=0)
    token_delta: int
    regressions: list[CaseChange] = Field(default_factory=list)
    improvements: list[CaseChange] = Field(default_factory=list)
    new_failures: list[CaseChange] = Field(default_factory=list)
    new_passes: list[CaseChange] = Field(default_factory=list)
    removed_cases: list[CaseChange] = Field(default_factory=list)

    def has_regressions(self) -> bool:
        """Strictly: at least one case that passed before now fails.

        New cases that are failing do **not** count as regressions —
        they're tracked separately under :attr:`new_failures` so a
        CI gate can distinguish "you broke an existing test" from
        "you added a new case that doesn't pass yet."
        """
        return bool(self.regressions)

    def has_new_failures(self) -> bool:
        """True when the current run added cases that fail."""
        return bool(self.new_failures)


def compute_eval_diff(baseline: EvalRunResult, current: EvalRunResult) -> EvalDiff:
    """Classify every case as one of the five :type:`ChangeKind` values.

    Cases match by ``case_name``. Two cases with the same name in
    baseline and current are considered the same case — even if the
    prompt changed underneath (the user is responsible for unique,
    stable case names; we don't try to fingerprint the prompt).

    ``token_delta`` is signed: positive when the current run spent
    more tokens than the baseline, negative when fewer.
    """
    baseline_index = {c.case_name: c for c in baseline.case_results}
    current_index = {c.case_name: c for c in current.case_results}

    regressions: list[CaseChange] = []
    improvements: list[CaseChange] = []
    new_failures: list[CaseChange] = []
    new_passes: list[CaseChange] = []
    removed: list[CaseChange] = []

    for name, current_case in current_index.items():
        baseline_case = baseline_index.get(name)
        if baseline_case is None:
            kind: ChangeKind = "new_pass" if current_case.passed else "new_failure"
            entry = _build_change(
                name=name,
                kind=kind,
                baseline=None,
                current=current_case,
            )
            (new_passes if current_case.passed else new_failures).append(entry)
            continue

        if baseline_case.passed and not current_case.passed:
            regressions.append(
                _build_change(
                    name=name,
                    kind="regression",
                    baseline=baseline_case,
                    current=current_case,
                )
            )
        elif not baseline_case.passed and current_case.passed:
            improvements.append(
                _build_change(
                    name=name,
                    kind="improvement",
                    baseline=baseline_case,
                    current=current_case,
                )
            )
        # Unchanged passes / failures: counted in totals, not listed per-case.

    for name, baseline_case in baseline_index.items():
        if name in current_index:
            continue
        removed.append(
            _build_change(
                name=name,
                kind="removed",
                baseline=baseline_case,
                current=None,
            )
        )

    return EvalDiff(
        suite_project=current.suite_project,
        baseline_total=len(baseline.case_results),
        current_total=len(current.case_results),
        baseline_pass_count=baseline.pass_count,
        current_pass_count=current.pass_count,
        token_delta=current.total_tokens - baseline.total_tokens,
        regressions=regressions,
        improvements=improvements,
        new_failures=new_failures,
        new_passes=new_passes,
        removed_cases=removed,
    )


def _build_change(
    *,
    name: str,
    kind: ChangeKind,
    baseline: EvalCaseResult | None,
    current: EvalCaseResult | None,
) -> CaseChange:
    """Assemble a :class:`CaseChange` from one or both sides.

    Centralizing the construction keeps the classifier loop above
    short and ensures every CaseChange carries the same shape
    regardless of which transition produced it.
    """
    reference = current if current is not None else baseline
    expected = reference.expected if reference is not None else None
    return CaseChange(
        case_name=name,
        kind=kind,
        baseline_passed=baseline.passed if baseline is not None else None,
        current_passed=current.passed if current is not None else None,
        expected=expected,
        baseline_actual=baseline.actual if baseline is not None else None,
        current_actual=current.actual if current is not None else None,
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_diff_cli(diff: EvalDiff) -> str:
    """Render the diff as human-readable text.

    Sections appear only when non-empty so a clean diff (no
    transitions) produces a compact "no changes" report.
    """
    parts: list[str] = [
        f"eval diff for {diff.suite_project}",
        f"  baseline:  {diff.baseline_pass_count}/{diff.baseline_total} passing",
        f"  current:   {diff.current_pass_count}/{diff.current_total} passing",
        f"  tokens:    {_signed(diff.token_delta)} vs baseline",
    ]
    parts.extend(_section("Regressions (was passing, now failing)", diff.regressions))
    parts.extend(_section("New failures (case added + failing)", diff.new_failures))
    parts.extend(_section("Removed cases (gone from current)", diff.removed_cases))
    parts.extend(_section("Improvements (was failing, now passing)", diff.improvements))
    parts.extend(_section("New passes (case added + passing)", diff.new_passes))

    if not any(
        [
            diff.regressions,
            diff.new_failures,
            diff.removed_cases,
            diff.improvements,
            diff.new_passes,
        ]
    ):
        parts.append("")
        parts.append("no changes vs baseline")

    return "\n".join(parts) + "\n"


def _section(title: str, changes: list[CaseChange]) -> list[str]:
    """Format one named bucket; return empty list when bucket is empty."""
    if not changes:
        return []
    lines: list[str] = ["", f"{title}:"]
    for change in changes:
        lines.append(f"  - {change.case_name}")
        if change.baseline_actual is not None or change.current_actual is not None:
            lines.append(f"    baseline: {change.baseline_actual or '(none)'}")
            lines.append(f"    current:  {change.current_actual or '(none)'}")
    return lines


def _signed(value: int) -> str:
    """Render an integer with an explicit sign (+12 / -5 / 0)."""
    if value > 0:
        return f"+{value}"
    return str(value)


def render_diff_json(diff: EvalDiff, *, indent: int | None = 2) -> str:
    """Render the diff as JSON. Delegates to Pydantic for schema fidelity."""
    return diff.model_dump_json(indent=indent)


__all__ = [
    "CaseChange",
    "ChangeKind",
    "EvalDiff",
    "compute_eval_diff",
    "render_diff_cli",
    "render_diff_json",
]
