"""Tests for the CLI integration of RAG — Phase 6.5."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()

_MINIMAL_RAG_CTX = textwrap.dedent(
    """\
    project = "DemoCorpus"
    artifacts = ["rag"]

    [rag]
    chunking_strategy = "semantic"
    chunk_target_tokens = 500
    chunk_overlap_tokens = 50
    chunk_min_tokens = 100
    chunk_max_tokens = 1500
    embedding_model = "voyage-3"
    freshness_policy = "30d"

    [[document]]
    source = "docs/**/*.md"
    tags = ["docs"]
    """
)


class TestParse:
    def test_parses_rag_ctx(self, tmp_path: Path) -> None:
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(_MINIMAL_RAG_CTX, encoding="utf-8")
        result = runner.invoke(app, ["parse", str(ctx)])
        assert result.exit_code == 0, result.output
        assert '"type": "rag"' in result.output
        assert '"chunking_strategy": "semantic"' in result.output


class TestLint:
    def test_clean_rag_returns_zero_diagnostics(self, tmp_path: Path) -> None:
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(_MINIMAL_RAG_CTX, encoding="utf-8")
        result = runner.invoke(app, ["lint", str(ctx)])
        assert result.exit_code == 0
        assert "R001" not in result.output
        assert "R002" not in result.output
        assert "R003" not in result.output
        assert "R004" not in result.output

    def test_lint_surfaces_r_rules(self, tmp_path: Path) -> None:
        # Missing embedding_model + freshness, plus header_aware override
        # without anchors → R003 + R004 + R005 fire.
        bad = textwrap.dedent(
            """\
            project = "Bad"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "semantic"
            chunk_target_tokens = 500
            chunk_overlap_tokens = 50
            chunk_min_tokens = 100
            chunk_max_tokens = 1500

            [[document]]
            source = "docs/*.md"
            chunking_override = "header_aware"
            """
        )
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(bad, encoding="utf-8")
        result = runner.invoke(app, ["lint", str(ctx)])
        assert "R003" in result.output  # freshness
        assert "R004" in result.output  # embedding model
        assert "R005" in result.output  # header_aware without anchors


class TestCompile:
    def test_compiles_to_rag_manifest(self, tmp_path: Path) -> None:
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(_MINIMAL_RAG_CTX, encoding="utf-8")
        result = runner.invoke(
            app,
            ["compile", str(ctx), "--target", "rag_manifest", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        manifest_path = tmp_path / "rag.manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["version"] == "1.0"
        assert manifest["project"] == "DemoCorpus"
        assert manifest["rag"]["chunking_strategy"] == "semantic"
        assert manifest["rag"]["embedding_model"] == "voyage-3"
        assert manifest["documents"][0]["source"] == "docs/**/*.md"


class TestAudit:
    def test_audit_picks_up_rag_ctx(self, tmp_path: Path) -> None:
        (tmp_path / "rag").mkdir()
        ctx = tmp_path / "rag" / "rag.ctx"
        ctx.write_text(_MINIMAL_RAG_CTX, encoding="utf-8")
        result = runner.invoke(app, ["audit", str(tmp_path)])
        assert result.exit_code == 0
        assert "rag.ctx" in result.output

    def test_audit_runs_r_rules_on_bad_rag(self, tmp_path: Path) -> None:
        bad = textwrap.dedent(
            """\
            project = "Bad"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "semantic"
            chunk_target_tokens = 500
            chunk_overlap_tokens = 50
            chunk_min_tokens = 100
            chunk_max_tokens = 1500

            [[document]]
            source = "docs/*.md"
            """
        )
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(bad, encoding="utf-8")
        result = runner.invoke(app, ["audit", str(tmp_path)])
        assert "R003" in result.output
        assert "R004" in result.output


class TestStatsTargetCoverage:
    def test_rag_ctx_counts_under_ctx_bucket(self, tmp_path: Path) -> None:
        ctx = tmp_path / "rag.ctx"
        ctx.write_text(_MINIMAL_RAG_CTX, encoding="utf-8")
        result = runner.invoke(app, ["stats", str(tmp_path)])
        assert result.exit_code == 0
        assert "ctx" in result.output
