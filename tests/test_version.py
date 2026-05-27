"""Guarantee that ``__version__`` matches the ``pyproject.toml`` version.

The release workflow refuses to publish if the git tag does not match
``__version__``. This test catches the same drift one CI step earlier,
so a release PR that forgot to bump one of the two fails fast.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import contextos

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"


def test_package_version_matches_pyproject() -> None:
    with _PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    assert contextos.__version__ == data["project"]["version"]
