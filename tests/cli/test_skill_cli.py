"""Tests for the CLI integration of SKILL.md — Phase 5.5."""

from __future__ import annotations

import textwrap
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()

_MINIMAL_SKILL_MD = textwrap.dedent(
    """\
    ---
    name: cli-test
    title: CLI test
    description: Triggers when the test harness invokes the skill via the CLI.
    example_invocation: Run the harness.
    ---

    # CLI test

    Body.
    """
)

_MINIMAL_SKILL_CTX = textwrap.dedent(
    """\
    project = "CliSkill"
    artifacts = ["skills"]

    [[skill]]
    name = "cli-skill"
    title = "CLI skill"
    description = "Triggers when the CLI compiles a .ctx file with a [[skill]] block."
    example_invocation = "Run the compile harness."
    """
)


class TestParse:
    def test_parses_skill_md_via_basename(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        path.write_text(_MINIMAL_SKILL_MD, encoding="utf-8")
        result = runner.invoke(app, ["parse", str(path)])
        assert result.exit_code == 0, result.output
        assert '"type": "skill"' in result.output
        assert '"name": "cli-test"' in result.output

    def test_parses_skill_md_via_explicit_target(self, tmp_path: Path) -> None:
        path = tmp_path / "any-name.md"
        path.write_text(_MINIMAL_SKILL_MD, encoding="utf-8")
        result = runner.invoke(app, ["parse", str(path), "--target", "anthropic_skill"])
        assert result.exit_code == 0, result.output
        assert '"type": "skill"' in result.output

    def test_parses_skill_section_in_ctx(self, tmp_path: Path) -> None:
        path = tmp_path / "skill.ctx"
        path.write_text(_MINIMAL_SKILL_CTX, encoding="utf-8")
        result = runner.invoke(app, ["parse", str(path)])
        assert result.exit_code == 0, result.output
        assert '"type": "skill"' in result.output
        assert '"name": "cli-skill"' in result.output


class TestLint:
    def test_lints_skill_md(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        # Body has no H1 → S005 will fire (info, not error).
        bad_skill = _MINIMAL_SKILL_MD.replace("# CLI test\n\nBody.", "Plain body.")
        path.write_text(bad_skill, encoding="utf-8")
        result = runner.invoke(app, ["lint", str(path)])
        assert "S005" in result.output

    def test_clean_skill_returns_zero_diagnostics(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        path.write_text(_MINIMAL_SKILL_MD, encoding="utf-8")
        result = runner.invoke(app, ["lint", str(path)])
        assert result.exit_code == 0
        assert "S001" not in result.output
        assert "S002" not in result.output


class TestCompile:
    def test_compiles_skill_ctx_to_skill_md(self, tmp_path: Path) -> None:
        src = tmp_path / "skill.ctx"
        src.write_text(_MINIMAL_SKILL_CTX, encoding="utf-8")
        result = runner.invoke(
            app,
            ["compile", str(src), "--target", "anthropic_skill", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        skill_md = tmp_path / "SKILL.md"
        assert skill_md.exists()
        body = skill_md.read_text(encoding="utf-8")
        assert body.startswith("---\n")
        assert "name: cli-skill" in body
        assert "title: CLI skill" in body
        assert "example_invocation:" in body


class TestAudit:
    def test_audit_finds_skill_md(self, tmp_path: Path) -> None:
        (tmp_path / "skills").mkdir()
        skill_path = tmp_path / "skills" / "SKILL.md"
        bad_skill = _MINIMAL_SKILL_MD.replace("# CLI test\n\nBody.", "Plain body.")
        skill_path.write_text(bad_skill, encoding="utf-8")
        result = runner.invoke(app, ["audit", str(tmp_path)])
        assert result.exit_code == 0
        assert "skills/SKILL.md" in result.output
        assert "S005" in result.output

    def test_audit_skips_unparseable_skill_md(self, tmp_path: Path) -> None:
        skill_path = tmp_path / "SKILL.md"
        skill_path.write_text("no frontmatter at all\n", encoding="utf-8")
        result = runner.invoke(app, ["audit", str(tmp_path)])
        assert result.exit_code == 0
        # Parse failure pushes the file into skipped, not silently dropped.
        assert "Skipped" in result.output or "skipped" in result.output


class TestStatsTargetCoverage:
    def test_skill_md_counts_under_anthropic_skill(self, tmp_path: Path) -> None:
        (tmp_path / "skills").mkdir()
        (tmp_path / "skills" / "SKILL.md").write_text(_MINIMAL_SKILL_MD, encoding="utf-8")
        result = runner.invoke(app, ["stats", str(tmp_path)])
        assert result.exit_code == 0
        assert "anthropic_skill" in result.output
