"""Structured fixes for ContextOS diagnostics — Phase 8.5.

The ``ctx fix`` CLI consumes this module. The LSP code-actions
surface (Phase 7.3) currently has its own X003 implementation;
follow-up work will unify the two so both paths share the structured
fix logic here.

Four fixes ship today:

- **F001** — lowercase ALL CAPS rule titles via sentence case.
- **X001** — strip ``TODO`` / ``FIXME`` / ``XXX`` / ``HACK`` markers
  at the start of rule titles.
- **X003** — strip the trailing ``?`` from a rule title.
- **S005** — prepend ``# <title>`` to a SKILL.md body that lacks an
  H1 (and has a non-empty body otherwise).

Each fix takes ``(text, Diagnostic) → TextEdit | None`` and stays
pure (no I/O, no module-level state).
"""

from __future__ import annotations

from contextos.fix.edit import TextEdit, apply_text_edit
from contextos.fix.runner import FixResult, fix_path
from contextos.fix.structured import compute_fix

__all__ = [
    "FixResult",
    "TextEdit",
    "apply_text_edit",
    "compute_fix",
    "fix_path",
]
