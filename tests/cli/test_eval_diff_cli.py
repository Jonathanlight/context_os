"""Smoke tests for the ctx eval-diff CLI subcommand — Phase 7.11."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()


def _write_run(
    path: Path,
    *,
    cases: list[tuple[str, bool]],
    tokens: int = 0,
) -> None:
    payload = {
        "suite_project": "Test",
        "target": "anthropic_skill",
        "total_tokens": tokens,
        "case_results": [
            {
                "case_name": name,
                "expected": "x",
                "actual": "x" if passed else "wrong",
                "passed": passed,
                "tokens_used": None,
                "error": None,
            }
            for name, passed in cases
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestEvalDiffExitCodes:
    def test_no_changes_exits_zero(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[("a", True)])
        _write_run(current, cases=[("a", True)])
        result = runner.invoke(app, ["eval-diff", str(baseline), str(current)])
        assert result.exit_code == 0
        assert "no changes vs baseline" in result.output

    def test_regression_exits_nonzero(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[("a", True)])
        _write_run(current, cases=[("a", False)])
        result = runner.invoke(app, ["eval-diff", str(baseline), str(current)])
        assert result.exit_code == 1
        assert "Regressions" in result.output

    def test_new_failure_alone_does_not_fail(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[])
        _write_run(current, cases=[("new-case", False)])
        # Default behavior: new failures don't break CI.
        result = runner.invoke(app, ["eval-diff", str(baseline), str(current)])
        assert result.exit_code == 0
        assert "New failures" in result.output

    def test_new_failure_with_flag_fails(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[])
        _write_run(current, cases=[("new-case", False)])
        result = runner.invoke(
            app,
            ["eval-diff", str(baseline), str(current), "--fail-on-new-failure"],
        )
        assert result.exit_code == 1

    def test_improvement_does_not_fail(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[("a", False)])
        _write_run(current, cases=[("a", True)])
        result = runner.invoke(app, ["eval-diff", str(baseline), str(current)])
        assert result.exit_code == 0
        assert "Improvements" in result.output


class TestEvalDiffJsonOutput:
    def test_json_shape(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        _write_run(baseline, cases=[("a", True)])
        _write_run(current, cases=[("a", False)])
        result = runner.invoke(
            app, ["eval-diff", str(baseline), str(current), "--json"]
        )
        # exit_code=1 because of the regression — but stdout still
        # contains valid JSON the CI step can consume.
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["suite_project"] == "Test"
        assert len(payload["regressions"]) == 1

    def test_output_file_written(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        out_path = tmp_path / "diff.json"
        _write_run(baseline, cases=[("a", True)])
        _write_run(current, cases=[("a", True)])
        result = runner.invoke(
            app,
            [
                "eval-diff",
                str(baseline),
                str(current),
                "--json",
                "--output",
                str(out_path),
            ],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert payload["regressions"] == []


class TestEvalDiffParseErrors:
    def test_malformed_baseline_surfaces_error(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        current = tmp_path / "current.json"
        baseline.write_text("not json at all", encoding="utf-8")
        _write_run(current, cases=[("a", True)])
        result = runner.invoke(app, ["eval-diff", str(baseline), str(current)])
        assert result.exit_code == 1
        assert "failed to parse" in result.output
