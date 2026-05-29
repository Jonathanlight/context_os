"""CLI tests for ``ctx create``, ``ctx init`` and ``ctx upgrade``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import contextos
from contextos.cli import app
from contextos.parsers import parse_ctx_string
from contextos.upgrade import UpgradeError

runner = CliRunner()


def test_create_writes_ctx_file_in_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["create", "demo", "--lang", "python,fastapi", "--domain", "fintech"],
    )

    assert result.exit_code == 0, result.stdout
    written = tmp_path / "demo.ctx"
    assert written.is_file()
    document = parse_ctx_string(written.read_text(encoding="utf-8"))
    assert document.agent is not None
    assert document.agent.stack is not None
    assert "python>=3.12" in document.agent.stack.required
    assert "fastapi" in document.agent.stack.required


def test_create_normalizes_user_facing_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["create", "demo", "--lang", "Next.js,react,TypeScript"],
    )

    assert result.exit_code == 0, result.stdout
    document = parse_ctx_string((tmp_path / "demo.ctx").read_text(encoding="utf-8"))
    assert document.agent is not None
    rule_ids = {rule.id for rule in document.agent.rules}
    assert "NXT-001" in rule_ids
    assert "RCT-001" in rule_ids
    assert "TS-001" in rule_ids


def test_create_warns_on_unknown_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["create", "demo", "--lang", "python,nope"])
    assert result.exit_code == 0
    # stderr is merged into stdout by typer.testing.CliRunner.
    assert "unknown language slug" in result.output


def test_create_refuses_to_overwrite_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo.ctx").write_text("project = 'demo'\n", encoding="utf-8")

    result = runner.invoke(app, ["create", "demo", "--lang", "python"])

    assert result.exit_code == 1
    assert "refusing to overwrite" in result.output


def test_create_force_overwrites_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo.ctx").write_text("project = 'old'\n", encoding="utf-8")

    result = runner.invoke(app, ["create", "demo", "--lang", "python", "--force"])

    assert result.exit_code == 0, result.output
    rewritten = (tmp_path / "demo.ctx").read_text(encoding="utf-8")
    assert 'project = "demo"' in rewritten or 'project = "demo"' in rewritten


def test_create_list_languages_prints_registry() -> None:
    result = runner.invoke(app, ["create", "--list-languages"])
    assert result.exit_code == 0
    assert "python" in result.output
    assert "symfony" in result.output


def test_init_detects_existing_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["fastapi>=0.110"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["init", str(tmp_path), "--project", "demo"])

    assert result.exit_code == 0, result.output
    assert "fastapi" in result.output
    written = tmp_path / "demo.ctx"
    assert written.is_file()
    document = parse_ctx_string(written.read_text(encoding="utf-8"))
    assert document.agent is not None
    assert document.agent.stack is not None
    assert "fastapi" in document.agent.stack.required


def test_init_dry_run_prints_document_without_writing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["django>=5"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--project", "demo", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "django" in result.output
    assert "DJG-001" in result.output  # rendered TOML reaches stdout
    assert not (tmp_path / "demo.ctx").exists()


def test_upgrade_check_reports_when_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "contextos.upgrade.check_latest_version",
        lambda *, include_prereleases=False: contextos.__version__,
    )

    result = runner.invoke(app, ["upgrade", "--check"])

    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_upgrade_check_announces_newer_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "contextos.upgrade.check_latest_version",
        lambda *, include_prereleases=False: "999.0.0",
    )

    result = runner.invoke(app, ["upgrade", "--check"])

    assert result.exit_code == 0
    assert "999.0.0" in result.output


def test_upgrade_reports_pypi_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_: Any) -> str:
        raise UpgradeError("pypi unreachable")

    monkeypatch.setattr("contextos.upgrade.check_latest_version", boom)

    result = runner.invoke(app, ["upgrade", "--check"])

    assert result.exit_code == 1
    assert "could not reach PyPI" in result.output


def test_eval_friendly_error_when_suite_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["eval", "skills.eval.toml", "--dry-run"])
    # Exit 2 (CLI usage error) + actionable hint pointing to eval-init.
    assert result.exit_code == 2
    assert "does not exist" in result.output
    assert "ctx eval-init" in result.output


def test_eval_init_scaffolds_skill_suite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["eval-init", "skills"])

    assert result.exit_code == 0, result.output
    suite = tmp_path / "skills.eval.toml"
    assert suite.is_file()
    text = suite.read_text(encoding="utf-8")
    assert 'project = "skills"' in text
    assert 'target = "anthropic_skill"' in text
    assert "[[skill_case]]" in text


def test_eval_init_scaffolds_rag_suite_with_custom_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "tests" / "policy.eval.toml"
    result = runner.invoke(
        app,
        ["eval-init", "policy", "--target", "rag", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert 'target = "rag"' in text
    assert "[[rag_case]]" in text


def test_eval_init_rejects_unknown_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["eval-init", "demo", "--target", "nonsense"])
    assert result.exit_code == 2
    assert "unknown --target" in result.output


def test_init_recurses_into_subdirs(tmp_path: Path) -> None:
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "pyproject.toml").write_text(
        '[project]\nname = "api"\ndependencies = ["fastapi>=0.110"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["init", str(tmp_path), "--project", "demo", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "fastapi" in result.output
    assert "api/" in result.output


def test_init_no_recursive_ignores_subdirs(tmp_path: Path) -> None:
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "pyproject.toml").write_text(
        '[project]\nname = "api"\ndependencies = ["fastapi>=0.110"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--project", "demo", "--dry-run", "--no-recursive"],
    )

    assert result.exit_code == 0, result.output
    # fastapi was nested -- with --no-recursive it must NOT be picked up.
    assert "fastapi" not in result.output


def test_upgrade_install_invokes_pip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "contextos.upgrade.check_latest_version",
        lambda *, include_prereleases=False: "999.0.0",
    )

    called: list[str | None] = []

    def fake_run_pip_upgrade(*, target_version: str | None = None) -> None:
        called.append(target_version)

    monkeypatch.setattr("contextos.upgrade.run_pip_upgrade", fake_run_pip_upgrade)

    result = runner.invoke(app, ["upgrade"])

    assert result.exit_code == 0, result.output
    assert called == ["999.0.0"]
