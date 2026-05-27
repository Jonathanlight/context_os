"""Smoke tests — the package imports and exposes a non-empty version."""

from __future__ import annotations

from typer.testing import CliRunner

import contextos
from contextos.__main__ import app


def test_package_imports() -> None:
    assert contextos.__version__


def test_version_is_string() -> None:
    assert isinstance(contextos.__version__, str)


def test_cli_version_flag() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert contextos.__version__ in result.stdout


def test_cli_no_args_shows_help() -> None:
    result = CliRunner().invoke(app, [])
    assert result.exit_code != 0  # no_args_is_help exits non-zero
    assert "ContextOS" in result.stdout
