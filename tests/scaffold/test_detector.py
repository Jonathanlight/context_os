"""Tests for the manifest-driven project detector.

Builds tiny fake repos under ``tmp_path`` and asserts the detector
finds the right languages with the right rationale lines. Tests stay
filesystem-level rather than mocking ``Path`` -- the whole point of
the detector is on-disk behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from contextos.scaffold import detect_project


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detect_symfony_repo(tmp_path: Path) -> None:
    composer = {
        "require": {
            "php": "^8.3",
            "symfony/framework-bundle": "^7.0",
            "doctrine/orm": "^3.0",
        },
    }
    _write(tmp_path / "composer.json", json.dumps(composer))

    result = detect_project(tmp_path)

    assert "symfony" in result.languages
    assert "doctrine" in result.languages
    assert "php" in result.languages
    # Framework ranked before the base language.
    assert result.languages.index("symfony") < result.languages.index("php")
    assert any("symfony" in line.lower() for line in result.rationale)


def test_detect_fastapi_pyproject(tmp_path: Path) -> None:
    pyproject = """
    [project]
    name = "demo"
    dependencies = ["fastapi>=0.110", "pydantic>=2.7"]
    """
    _write(tmp_path / "pyproject.toml", pyproject)

    result = detect_project(tmp_path)

    assert "fastapi" in result.languages
    assert "python" in result.languages


def test_detect_nextjs_react_typescript(tmp_path: Path) -> None:
    package = {
        "dependencies": {"next": "^15.0.0", "react": "^19.0.0"},
        "devDependencies": {"typescript": "^5.4.0"},
    }
    _write(tmp_path / "package.json", json.dumps(package))

    result = detect_project(tmp_path)

    assert "nextjs" in result.languages
    assert "react" in result.languages
    assert "typescript" in result.languages
    assert "node" in result.languages


def test_detect_flutter_pubspec(tmp_path: Path) -> None:
    pubspec = """
    name: demo
    dependencies:
      flutter:
        sdk: flutter
      cupertino_icons: ^1.0
    """
    _write(tmp_path / "pubspec.yaml", pubspec)

    result = detect_project(tmp_path)

    assert "flutter" in result.languages
    assert "dart" in result.languages


def test_detect_go_with_gin(tmp_path: Path) -> None:
    go_mod = "module example.com/x\n\nrequire github.com/gin-gonic/gin v1.10.0\n"
    _write(tmp_path / "go.mod", go_mod)

    result = detect_project(tmp_path)

    assert "gin" in result.languages
    assert "go" in result.languages


def test_detect_rust_with_axum(tmp_path: Path) -> None:
    cargo = """
    [package]
    name = "x"

    [dependencies]
    axum = "0.7"
    """
    _write(tmp_path / "Cargo.toml", cargo)

    result = detect_project(tmp_path)

    assert "axum" in result.languages
    assert "rust" in result.languages


def test_detect_empty_repo_returns_no_languages(tmp_path: Path) -> None:
    result = detect_project(tmp_path)
    assert result.languages == []
    assert result.rationale == []


def test_detect_infra_signals(tmp_path: Path) -> None:
    _write(tmp_path / "Dockerfile", "FROM scratch\n")
    _write(tmp_path / ".github" / "workflows" / "ci.yml", "name: ci\n")
    _write(tmp_path / "main.tf", "# tf\n")

    result = detect_project(tmp_path)

    assert "docker" in result.languages
    assert "github-actions" in result.languages
    assert "terraform" in result.languages
