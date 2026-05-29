"""Self-update helper used by the ``ctx upgrade`` command.

Two responsibilities:

- :func:`check_latest_version` queries the PyPI JSON API for the
  newest version of ``context-os-ctx``. Pre-releases are filtered
  out unless the caller opts in -- standard pip semantics.
- :func:`run_pip_upgrade` shells out to ``python -m pip install
  --upgrade`` so the existing ``ctx`` interpreter resolves the new
  wheel against the same environment it already lives in.

Both raise :class:`UpgradeError` on every recoverable failure
(network down, PyPI 5xx, pip non-zero exit) so the CLI layer can
report a single line and exit cleanly.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

PACKAGE_NAME = "context-os-ctx"
"""PyPI distribution name -- matches the ``project.name`` in pyproject.toml."""

_PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
"""Stable PyPI JSON metadata endpoint -- documented at warehouse/api."""

# PEP 440 final-release pattern: digits separated by dots, no pre/post/dev tags.
_FINAL_RELEASE = re.compile(r"^\d+(\.\d+)*$")


class UpgradeError(RuntimeError):
    """Raised by ``ctx upgrade`` when PyPI or pip refuses to cooperate."""


def check_latest_version(*, include_prereleases: bool = False) -> str:
    """Return the newest published version of ``context-os-ctx`` on PyPI.

    :param include_prereleases: when False (the default) ``1.2.3rc1``
        and similar are skipped -- mirrors ``pip install`` without
        ``--pre``.
    :raises UpgradeError: on network failure, JSON parse error, or
        empty release list.
    """
    try:
        request = Request(_PYPI_URL, headers={"Accept": "application/json"})
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        msg = f"failed to query {_PYPI_URL}: {exc}"
        raise UpgradeError(msg) from exc

    releases = payload.get("releases", {})
    if not isinstance(releases, dict) or not releases:
        msg = "PyPI returned no release metadata for context-os-ctx"
        raise UpgradeError(msg)

    candidates = [
        version
        for version, files in releases.items()
        if files and (include_prereleases or _FINAL_RELEASE.match(version))
    ]
    if not candidates:
        msg = "no eligible release versions found on PyPI"
        raise UpgradeError(msg)

    return str(max(candidates, key=_version_key))


def run_pip_upgrade(*, target_version: str | None = None) -> None:
    """Invoke ``pip install --upgrade context-os-ctx`` in-process.

    Uses :data:`sys.executable` so the upgrade hits the same
    interpreter ``ctx`` runs under (avoids the classic "I upgraded
    but `ctx --version` still reports the old build" trap when
    multiple Pythons are on PATH).

    :raises UpgradeError: when pip exits non-zero.
    """
    spec = PACKAGE_NAME if target_version is None else f"{PACKAGE_NAME}=={target_version}"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", spec]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        msg = f"pip install --upgrade failed with exit code {exc.returncode}"
        raise UpgradeError(msg) from exc


def _version_key(version: str) -> tuple[int, ...]:
    """Numeric-aware ordering for final-release versions.

    Strips PEP 440 pre/post/dev tags so the comparison is monotonic
    on the components we actually care about ranking. Versions that
    don't parse as digits sink to ``(0,)`` so they never win the
    ``max`` lookup -- the prefiltering by :data:`_FINAL_RELEASE`
    already removes them in the default code path.
    """
    parts: list[int] = []
    for chunk in version.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


__all__ = [
    "PACKAGE_NAME",
    "UpgradeError",
    "check_latest_version",
    "run_pip_upgrade",
]
