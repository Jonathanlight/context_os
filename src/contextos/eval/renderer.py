"""Renderers for :class:`EvalRunResult` — Phase 7.10.

Two output shapes: human-readable CLI text (for ``ctx eval`` direct
use) and structured JSON (for ``--json`` mode, CI consumption, and
the Phase 7.11 baseline diff). Both are pure functions over the
:class:`EvalRunResult` so they round-trip without needing a runner.
"""

from __future__ import annotations

from contextos.eval.results import EvalRunResult


def render_eval_cli(result: EvalRunResult) -> str:
    """Render the run as human-readable text.

    Layout: a header block (suite project, target, pass rate, token
    spend) followed by one line per case. Failing cases get the
    expected / actual / error fields inlined; passing cases stay
    terse so a clean run produces a compact report.
    """
    total = len(result.case_results)
    parts: list[str] = [
        f"eval suite: {result.suite_project}",
        f"target:     {result.target}",
        f"pass:       {result.pass_count}/{total} ({result.pass_rate:.0%})",
        f"tokens:     {result.total_tokens}",
        "",
    ]
    if not result.case_results:
        parts.append("no cases run")
        return "\n".join(parts).rstrip() + "\n"

    for case in result.case_results:
        status = "PASS" if case.passed else "FAIL"
        parts.append(f"  [{status}] {case.case_name}")
        if not case.passed:
            parts.append(f"    expected: {case.expected}")
            parts.append(f"    actual:   {case.actual if case.actual is not None else '(none)'}")
            if case.error:
                parts.append(f"    error:    {case.error}")

    return "\n".join(parts) + "\n"


def render_eval_json(result: EvalRunResult, *, indent: int | None = 2) -> str:
    """Render the run as JSON.

    Delegates to Pydantic's ``model_dump_json`` so the schema stays in
    sync with the model definitions in :mod:`contextos.eval.results`.
    The default indent matches what ``ctx audit --json`` produces for
    consistency across CLI subcommands.
    """
    return result.model_dump_json(indent=indent)


__all__ = ["render_eval_cli", "render_eval_json"]
