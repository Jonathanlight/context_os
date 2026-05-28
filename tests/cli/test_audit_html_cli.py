"""Smoke tests for ctx audit --html — Phase 8.3."""

from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()


class TestAuditHtmlCli:
    def test_html_flag_emits_html_to_stdout(self, tmp_path: Path) -> None:
        # An empty repo audit; verifies the flag plumbs through.
        result = runner.invoke(app, ["audit", str(tmp_path), "--html"])
        assert result.exit_code == 0
        assert "<!doctype html>" in result.output

    def test_html_with_output_file(self, tmp_path: Path) -> None:
        out_path = tmp_path / "report.html"
        result = runner.invoke(
            app,
            ["audit", str(tmp_path), "--html", "--output", str(out_path)],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert text.startswith("<!doctype html>")

    def test_html_with_diagnostic(self, tmp_path: Path) -> None:
        # Drop a CLAUDE.md that produces an A001 vague-directive warning.
        claude = tmp_path / "CLAUDE.md"
        claude.write_text(
            textwrap.dedent(
                """\
                # MyApp

                ## Rules

                - Be concise.
                """
            ),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["audit", str(tmp_path), "--html"])
        assert result.exit_code == 0
        assert "CLAUDE.md" in result.output
        # Filters present.
        assert 'data-filter="warning"' in result.output

    def test_json_and_html_mutually_exclusive(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["audit", str(tmp_path), "--html", "--json"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output
