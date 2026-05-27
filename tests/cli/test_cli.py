"""CLI tests via ``typer.testing.CliRunner``."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from typer.testing import CliRunner

import contextos
from contextos.cli import app

runner = CliRunner()

_MINIMAL_CTX = textwrap.dedent(
    """
    project = "CLISample"
    [[rules]]
    id = "X-001"
    title = "Use type hints"
    severity = "must"
    """
).strip()


def _write_ctx(tmp_path: Path, content: str = _MINIMAL_CTX) -> Path:
    path = tmp_path / "sample.ctx"
    path.write_text(content, encoding="utf-8")
    return path


def _write_md(tmp_path: Path) -> Path:
    path = tmp_path / "CLAUDE.md"
    path.write_text("# CLISample\n\n## Rules\n\n- Use type hints.\n", encoding="utf-8")
    return path


class TestVersion:
    def test_long_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert contextos.__version__ in result.stdout

    def test_short_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert contextos.__version__ in result.stdout


class TestNoArgs:
    def test_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer's no_args_is_help exits with a non-zero code.
        assert result.exit_code != 0
        assert "ContextOS" in result.stdout


class TestParseCtx:
    def test_default_output_is_json(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        result = runner.invoke(app, ["parse", str(ctx)])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["project"] == "CLISample"
        assert payload["type"] == "agent"

    def test_to_ctx_emits_toml(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        result = runner.invoke(app, ["parse", str(ctx), "--to-ctx"])
        assert result.exit_code == 0
        assert 'project = "CLISample"' in result.stdout

    def test_output_writes_to_file(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        out = tmp_path / "out.json"
        result = runner.invoke(app, ["parse", str(ctx), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["project"] == "CLISample"

    def test_missing_file_errors(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["parse", str(tmp_path / "missing.ctx")])
        # Typer's path validator catches non-existent files itself.
        assert result.exit_code != 0

    def test_parse_error_returns_nonzero(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.ctx"
        bad.write_text('project = "X"\n[[rules]]\nid = "lower"\ntitle = "t"\nseverity = "must"\n')
        result = runner.invoke(app, ["parse", str(bad)])
        assert result.exit_code == 1
        # Error printed to stderr (CliRunner merges into result.stderr).
        assert "[[rules]]" in (result.stderr or "")


class TestParseMarkdown:
    def test_markdown_requires_target(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path)
        result = runner.invoke(app, ["parse", str(md)])
        assert result.exit_code == 1
        assert "--target is required" in (result.stderr or "")

    def test_markdown_with_target(self, tmp_path: Path) -> None:
        md = _write_md(tmp_path)
        result = runner.invoke(app, ["parse", str(md), "--target", "claude_code"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["project"] == "CLISample"


class TestCompile:
    def test_default_writes_to_stdout(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        result = runner.invoke(app, ["compile", str(ctx), "--target", "claude_code"])
        assert result.exit_code == 0
        assert "# CLISample" in result.stdout
        assert "## Rules" in result.stdout

    def test_output_dir_writes_file(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        out_dir = tmp_path / "out"
        result = runner.invoke(
            app,
            ["compile", str(ctx), "--target", "claude_code", "--output-dir", str(out_dir)],
        )
        assert result.exit_code == 0
        written = out_dir / "CLAUDE.md"
        assert written.exists()
        body = written.read_text(encoding="utf-8")
        assert body.startswith("# CLISample")

    def test_output_dir_creates_missing_parent(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        out_dir = tmp_path / "nested" / "out"
        result = runner.invoke(
            app,
            ["compile", str(ctx), "--target", "claude_code", "--output-dir", str(out_dir)],
        )
        assert result.exit_code == 0
        assert (out_dir / "CLAUDE.md").exists()

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        out_dir = tmp_path / "out"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ctx),
                "--target",
                "claude_code",
                "--output-dir",
                str(out_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "dry-run: would write CLAUDE.md" in result.stdout
        assert "# CLISample" in result.stdout
        # Output dir is NOT created in dry-run.
        assert not (out_dir / "CLAUDE.md").exists()

    def test_unknown_target_errors(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        result = runner.invoke(app, ["compile", str(ctx), "--target", "gpt"])
        assert result.exit_code == 1
        assert "unknown --target 'gpt'" in (result.stderr or "")

    def test_missing_file_errors(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["compile", str(tmp_path / "missing.ctx"), "--target", "claude_code"],
        )
        assert result.exit_code != 0

    def test_parse_error_returns_nonzero(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.ctx"
        bad.write_text('artifacts = ["context"]\n')  # missing project
        result = runner.invoke(app, ["compile", str(bad), "--target", "claude_code"])
        assert result.exit_code == 1
        assert "missing or empty" in (result.stderr or "")


class TestLint:
    def test_clean_ctx_reports_no_diagnostics(self, tmp_path: Path) -> None:
        ctx = _write_ctx(tmp_path)
        result = runner.invoke(app, ["lint", str(ctx)])
        assert result.exit_code == 0
        assert "no diagnostics" in result.stdout

    def test_vague_directive_triggers_a001(self, tmp_path: Path) -> None:
        ctx = tmp_path / "vague.ctx"
        ctx.write_text(
            'project = "X"\n[[rules]]\nid = "STYLE-001"\ntitle = "Be concise"\nseverity = "must"\n'
        )
        result = runner.invoke(app, ["lint", str(ctx)])
        # Warning-level diagnostic — exit code stays 0 (no errors).
        assert result.exit_code == 0
        assert "warning[A001]" in result.stdout
        assert "Be concise" in result.stdout

    def test_json_output(self, tmp_path: Path) -> None:
        ctx = tmp_path / "vague.ctx"
        ctx.write_text(
            'project = "X"\n[[rules]]\nid = "STYLE-001"\ntitle = "Be concise"\nseverity = "must"\n'
        )
        result = runner.invoke(app, ["lint", str(ctx), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload[0]["code"] == "A001"
        assert payload[0]["severity"] == "warning"

    def test_markdown_input_with_target(self, tmp_path: Path) -> None:
        md = tmp_path / "CLAUDE.md"
        md.write_text("# X\n\n## Rules\n\n- Be concise\n")
        result = runner.invoke(app, ["lint", str(md), "--target", "claude_code"])
        assert result.exit_code == 0
        assert "A001" in result.stdout
