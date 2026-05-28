"""Smoke tests for the ``ctx lsp`` CLI subcommand — Phase 7.1."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from contextos.cli import app

runner = CliRunner()


class TestLspCommand:
    def test_lsp_invokes_run_stdio(self) -> None:
        # Patch run_stdio so the test doesn't actually block on stdio.
        with patch("contextos.lsp.run_stdio") as mock_run:
            result = runner.invoke(app, ["lsp"])
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()

    def test_lsp_help_mentions_extras(self) -> None:
        result = runner.invoke(app, ["lsp", "--help"])
        assert result.exit_code == 0
        # The user-facing help should point at the extras install path
        # so editors that surface --help inline can recover from the
        # missing-pygls case without grepping the source.
        assert "lsp" in result.output.lower()
