"""Tests for the recursive ``detect_project`` mode used by ``ctx init``.

A real-world repo often spreads multiple manifests across sub-trees
(e.g. ``frontend/package.json`` next to ``api/composer.json`` and a
``infra/`` with a Dockerfile). The v4.1 detector only scanned the
root and missed everything below; these tests pin the new
behaviour: recursive by default, capped by ``max_depth``, and
honouring :data:`SKIP_DIRECTORIES`.
"""

from __future__ import annotations

import json
from pathlib import Path

from contextos.scaffold import detect_project
from contextos.scaffold.detector import SKIP_DIRECTORIES


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_recursive_detect_discovers_nested_manifests(tmp_path: Path) -> None:
    # Symfony root + nested Angular client + nested Python data pipeline.
    _write(
        tmp_path / "composer.json",
        json.dumps({"require": {"symfony/framework-bundle": "^7.0"}}),
    )
    _write(
        tmp_path / "client" / "package.json",
        json.dumps({"dependencies": {"@angular/core": "^18.0.0"}}),
    )
    _write(
        tmp_path / "data" / "pyproject.toml",
        '[project]\nname = "data"\ndependencies = ["fastapi>=0.110"]\n',
    )

    result = detect_project(tmp_path)

    assert {"symfony", "php", "angular", "node", "fastapi", "python"} <= set(result.languages)
    # Rationale exposes the relative path so the operator can read why.
    assert any("client/" in line for line in result.rationale)
    assert any("data/" in line for line in result.rationale)


def test_no_recursive_only_inspects_root(tmp_path: Path) -> None:
    _write(
        tmp_path / "composer.json",
        json.dumps({"require": {"symfony/framework-bundle": "^7.0"}}),
    )
    _write(
        tmp_path / "client" / "package.json",
        json.dumps({"dependencies": {"@angular/core": "^18.0.0"}}),
    )

    result = detect_project(tmp_path, recursive=False)

    assert "symfony" in result.languages
    assert "php" in result.languages
    assert "angular" not in result.languages


def test_max_depth_caps_the_recursion(tmp_path: Path) -> None:
    # Manifest at depth 3 -- visible at depth>=3, hidden at depth=2.
    deep = tmp_path / "a" / "b" / "c"
    _write(
        deep / "package.json",
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
    )
    # Intermediate dirs need a manifest too so the walker reaches them
    # (the walker only descends when a manifest indicates a sub-project).
    for parent in (tmp_path / "a", tmp_path / "a" / "b"):
        _write(parent / "package.json", json.dumps({"name": "marker"}))

    shallow = detect_project(tmp_path, max_depth=2)
    deeper = detect_project(tmp_path, max_depth=4)

    assert "react" not in shallow.languages
    assert "react" in deeper.languages


def test_skip_directories_is_not_recursed_into(tmp_path: Path) -> None:
    # node_modules contains a manifest -- must NOT be detected.
    _write(
        tmp_path / "node_modules" / "react" / "package.json",
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
    )
    _write(tmp_path / "src" / "package.json", json.dumps({"name": "demo"}))

    result = detect_project(tmp_path)

    # node_modules was skipped -- React isn't promoted from a vendored copy.
    assert "react" not in result.languages
    # Sanity: the skip list actually contains it.
    assert "node_modules" in SKIP_DIRECTORIES


def test_recursive_skips_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "external"
    _write(target / "package.json", json.dumps({"dependencies": {"vue": "^3.0.0"}}))

    link = tmp_path / "link"
    link.symlink_to(target)

    # Even though external/ has a manifest, the symlink path is skipped --
    # but the direct ``external`` directory still gets scanned.
    result = detect_project(tmp_path)
    assert "vue" in result.languages
    # No duplicate rationale line from the symlink traversal.
    vue_lines = [line for line in result.rationale if "Vue" in line]
    assert len(vue_lines) == 1
