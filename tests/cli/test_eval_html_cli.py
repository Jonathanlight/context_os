"""Smoke tests for ctx eval --html — Phase 8.4."""

from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()

_SKILL_SUITE = textwrap.dedent(
    """\
    project = "Test"
    target = "anthropic_skill"

    [[skill_case]]
    name = "a"
    prompt = "Do the thing."
    expected_skill = "demo"
    """
)


class TestEvalHtmlCli:
    def test_html_flag_emits_html(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run", "--html"])
        assert result.exit_code == 0
        assert "<!doctype html>" in result.output
        assert "ContextOS eval" in result.output

    def test_html_with_output_file(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        out_path = tmp_path / "report.html"
        result = runner.invoke(
            app,
            ["eval", str(suite), "--dry-run", "--html", "--output", str(out_path)],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert "<!doctype html>" in text

    def test_json_and_html_mutually_exclusive(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run", "--html", "--json"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    def test_html_includes_pass_rate(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run", "--html"])
        # Dry-run always passes by construction → 100%.
        assert ">100%<" in result.output
