"""Scaffolding -- ``ctx create`` and ``ctx init``.

Two related entry points:

- :func:`build_starter_document` -- pure constructor that takes a
  project name + language list and returns a :class:`Document`.
  Backs ``ctx create``.
- :func:`detect_project` -- inspect a repo root for known manifest
  files and return a :class:`DetectedProject`. Backs ``ctx init``.

The CLI layer composes the two: ``ctx init`` calls
:func:`detect_project` then forwards the detected languages to
:func:`build_starter_document` to get the same shape ``ctx create``
would produce.
"""

from __future__ import annotations

from contextos.scaffold.builder import build_starter_document
from contextos.scaffold.detector import DetectedProject, detect_project
from contextos.scaffold.templates import (
    BASELINE_RULES,
    LANGUAGE_ALIASES,
    LANGUAGE_TEMPLATES,
    display_name,
    known_languages,
    known_languages_by_category,
    known_languages_by_wave,
    normalize_slug,
)

__all__ = [
    "BASELINE_RULES",
    "LANGUAGE_ALIASES",
    "LANGUAGE_TEMPLATES",
    "DetectedProject",
    "build_starter_document",
    "detect_project",
    "display_name",
    "known_languages",
    "known_languages_by_category",
    "known_languages_by_wave",
    "normalize_slug",
]
