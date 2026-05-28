"""``ctx fix`` runner — walks files, computes structured fixes, applies them.

The runner is path-driven, not analyzer-driven: callers pass a file
or directory and get back a :class:`FixResult` for each file that
had at least one applicable fix. Directories use the existing audit
scanner so the discovery rules (CLAUDE.md / AGENTS.md / SKILL.md /
*.ctx) stay consistent across ``ctx audit`` and ``ctx fix``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from contextos.audit import scan_repo
from contextos.fix.edit import TextEdit, apply_text_edits
from contextos.fix.structured import compute_fix

if TYPE_CHECKING:
    from contextos.diagnostics import Diagnostic


class FixResult(BaseModel):
    """Outcome of running ``compute_fix`` on every diagnostic in one file."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    path: Path
    original_text: str
    new_text: str
    applied_codes: list[str] = Field(default_factory=list)

    def changed(self) -> bool:
        """True when the fix produced a different file body."""
        return self.original_text != self.new_text


def fix_path(target: Path) -> list[FixResult]:
    """Run the structured fixes on ``target`` (file or directory).

    Returns one :class:`FixResult` per file that had at least one
    diagnostic with a structured fix available, **whether or not the
    final text changed**. Callers can use ``result.changed()`` to
    filter; we keep the no-op results so the report can still mention
    "I considered F001 here but the fix was a no-op."
    """
    paths = _expand(target)
    results: list[FixResult] = []
    for path in paths:
        result = _fix_one(path)
        if result is not None:
            results.append(result)
    return results


def _expand(target: Path) -> list[Path]:
    """Resolve ``target`` into the set of files to consider."""
    if target.is_file():
        return [target]
    if not target.is_dir():
        msg = f"target {target} is neither a file nor a directory"
        raise ValueError(msg)
    project = scan_repo(target)
    paths: list[Path] = []
    for agent_entry in project.agent_files:
        paths.append(agent_entry.path)
    for skill_entry in project.skill_files:
        paths.append(skill_entry.path)
    return sorted(paths)


def _fix_one(path: Path) -> FixResult | None:
    """Apply structured fixes to one file, return result or None when ineligible."""
    # Late import — keep the heavy parsers/analyzers out of the
    # module-load path for users who just need apply_text_edit.
    from contextos.analyzers import lint_document  # noqa: PLC0415
    from contextos.parsers import (  # noqa: PLC0415
        ContextOSParseError,
        parse_ctx_file,
        parse_skill_file,
    )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        if path.suffix.lower() == ".ctx":
            doc = parse_ctx_file(path)
        elif path.name == "SKILL.md":
            doc = parse_skill_file(path)
        else:
            from contextos.parsers import parse_markdown_file  # noqa: PLC0415

            target = _target_for_path(path)
            if target is None:
                return None
            doc = parse_markdown_file(path, target=target)
    except ContextOSParseError:
        return None

    bag = lint_document(doc, source=str(path))
    edits = list(_edits_from_bag(text, bag))
    if not edits:
        return None

    new_text = apply_text_edits(text, [edit for _code, edit in edits])
    return FixResult(
        path=path,
        original_text=text,
        new_text=new_text,
        applied_codes=[code for code, _edit in edits],
    )


def _edits_from_bag(text: str, bag: Iterable[Diagnostic]) -> Iterable[tuple[str, TextEdit]]:
    """Yield (code, TextEdit) pairs for each diagnostic that has a fix."""
    for diag in bag:
        edit = compute_fix(text, diag)
        if edit is not None:
            yield diag.code, edit


def _target_for_path(path: Path) -> str | None:
    """Pick the markdown parser target for the auto-detected basenames."""
    name = path.name
    if name == "CLAUDE.md":
        return "claude_code"
    if name == "AGENTS.md":
        return "codex"
    return None


__all__ = ["FixResult", "fix_path"]
