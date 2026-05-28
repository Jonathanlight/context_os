"""Smoke tests for the ctx eval CLI subcommand — Phase 7.10."""

from __future__ import annotations

import json
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

    [[skill_case]]
    name = "b"
    prompt = "Do the other thing."
    expected_skill = "demo"
    """
)


_RAG_SUITE = textwrap.dedent(
    """\
    project = "TestCorpus"
    target = "rag"

    [[rag_case]]
    name = "a"
    query = "What is X?"
    expected_sources = ["docs/x.md"]
    top_k = 3
    """
)


class TestDryRunSkill:
    def test_all_cases_pass(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "pass:       2/2 (100%)" in result.output
        assert "[PASS] a" in result.output
        assert "[PASS] b" in result.output

    def test_json_output_shape(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["suite_project"] == "Test"
        assert payload["target"] == "anthropic_skill"
        assert len(payload["case_results"]) == 2
        assert all(r["passed"] for r in payload["case_results"])

    def test_output_file_written(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        out_path = tmp_path / "result.json"
        result = runner.invoke(
            app,
            ["eval", str(suite), "--dry-run", "--json", "--output", str(out_path)],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        assert payload["suite_project"] == "Test"


class TestDryRunRag:
    def test_rag_dry_run_passes(self, tmp_path: Path) -> None:
        suite = tmp_path / "rag.eval.toml"
        suite.write_text(_RAG_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run"])
        assert result.exit_code == 0
        assert "pass:       1/1 (100%)" in result.output
        assert "target:     rag" in result.output


class TestLiveModeRequiresFlags:
    def test_skill_eval_without_dry_run_or_skills_dir_fails(self, tmp_path: Path) -> None:
        suite = tmp_path / "skill.eval.toml"
        suite.write_text(_SKILL_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite)])
        assert result.exit_code == 1
        assert "skills-dir" in result.output

    def test_rag_eval_without_dry_run_or_chunks_fails(self, tmp_path: Path) -> None:
        suite = tmp_path / "rag.eval.toml"
        suite.write_text(_RAG_SUITE, encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite)])
        assert result.exit_code == 1
        assert "rag-chunks" in result.output


class TestSuiteParseError:
    def test_invalid_suite_surfaces_error(self, tmp_path: Path) -> None:
        suite = tmp_path / "broken.eval.toml"
        # No `target` field -> Pydantic validation error.
        suite.write_text('project = "X"\n', encoding="utf-8")
        result = runner.invoke(app, ["eval", str(suite), "--dry-run"])
        assert result.exit_code == 1
        assert "validation" in result.output.lower()
