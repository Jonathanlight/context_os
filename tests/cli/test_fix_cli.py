"""Smoke tests for ctx fix CLI — Phase 8.5."""

from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()

_CTX_WITH_X003 = textwrap.dedent(
    """\
    project = "Test"
    artifacts = ["context"]

    [[rules]]
    id = "DOC-001"
    title = "Why log everything?"
    severity = "should"
    rationale = "Document for clarity."
    """
)


class TestFixDryRun:
    def test_default_is_dry_run(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(_CTX_WITH_X003, encoding="utf-8")
        result = runner.invoke(app, ["fix", str(ctx_file)])
        assert result.exit_code == 0
        assert "dry-run" in result.output
        # File NOT modified.
        assert ctx_file.read_text(encoding="utf-8") == _CTX_WITH_X003

    def test_dry_run_shows_diff(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(_CTX_WITH_X003, encoding="utf-8")
        result = runner.invoke(app, ["fix", str(ctx_file)])
        # Unified diff markers.
        assert "---" in result.output
        assert "+++" in result.output
        # The proposed change strips the question mark.
        assert "Why log everything" in result.output


class TestFixApply:
    def test_apply_writes_file(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(_CTX_WITH_X003, encoding="utf-8")
        result = runner.invoke(app, ["fix", str(ctx_file), "--apply"])
        assert result.exit_code == 0
        new_content = ctx_file.read_text(encoding="utf-8")
        assert "Why log everything?" not in new_content
        assert "Why log everything" in new_content
        assert "wrote" in result.output


class TestNoFixesNeeded:
    def test_clean_file_reports_no_diagnostics(self, tmp_path: Path) -> None:
        clean = textwrap.dedent(
            """\
            project = "Test"
            artifacts = ["context"]

            [[rules]]
            id = "DOC-001"
            title = "Stay calm"
            severity = "should"
            rationale = "Why."
            example_good = "x"
            """
        )
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(clean, encoding="utf-8")
        result = runner.invoke(app, ["fix", str(ctx_file)])
        assert result.exit_code == 0
        assert "no fixable diagnostics" in result.output


class TestDirectoryTarget:
    def test_directory_walk(self, tmp_path: Path) -> None:
        (tmp_path / "a.ctx").write_text(_CTX_WITH_X003, encoding="utf-8")
        result = runner.invoke(app, ["fix", str(tmp_path)])
        assert result.exit_code == 0
        assert "a.ctx" in result.output
