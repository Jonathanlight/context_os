"""Structured fixes by diagnostic code — Phase 8.5.

Each fix is a pure function over (text, Diagnostic) returning a
:class:`TextEdit` or ``None`` when no automatic fix is possible.

The dispatcher :func:`compute_fix` routes by ``diag.code`` and keeps
the rule-id check explicit so a future PR sees the supported
transforms in one place. Adding a new structured fix is one branch
plus a helper.

Fix design notes:

- **Conservative**: when in doubt, return ``None`` rather than
  produce a possibly-wrong edit. The CLI re-runs lint after each
  pass; a fix that doesn't fire just leaves the diagnostic for a
  human.
- **Single-edit**: each function returns at most one
  :class:`TextEdit`. Multi-edit fixes (e.g. moving a URL out of a
  title into ``links``) would need additional plumbing — out of
  scope for 8.5.
- **Idempotent**: applying a fix and re-running it on the result
  produces the same output. F001 lowercases an already-lowercased
  title to itself; X001 / X003 leave clean titles untouched.
"""

from __future__ import annotations

import re

from contextos.diagnostics import Diagnostic
from contextos.fix.edit import TextEdit

# Title-line regex: TOML key=value with double-quoted value.
_TITLE_LINE = re.compile(r'^(?P<lead>\s*title\s*=\s*")(?P<value>[^"]*)(?P<trail>".*)$')

# Markers X001 strips when they sit at the start of a rule title.
_X001_MARKERS = ("TODO", "FIXME", "XXX", "HACK")
_X001_MARKER_PATTERN = re.compile(
    r"^(?P<marker>(?:" + "|".join(_X001_MARKERS) + r"))[:\s]+",
    re.IGNORECASE,
)


def compute_fix(text: str, diag: Diagnostic) -> TextEdit | None:
    """Dispatch to the per-code helper, or return None.

    The dispatch table stays an explicit ``if`` ladder so the set of
    supported fixes is one ``Cmd+F diag.code`` away in code review.
    """
    if diag.code == "X003":
        return _fix_x003(text, diag)
    if diag.code == "F001":
        return _fix_f001(text, diag)
    if diag.code == "X001":
        return _fix_x001(text, diag)
    if diag.code == "S005":
        return _fix_s005(text, diag)
    return None


# ---------------------------------------------------------------------------
# Per-code implementations
# ---------------------------------------------------------------------------


def _fix_x003(text: str, diag: Diagnostic) -> TextEdit | None:
    """Strip the trailing ``?`` from a rule title."""
    line_index = _find_rule_title_line(text, diag)
    if line_index is None:
        return None
    lines = text.splitlines(keepends=False)
    line = lines[line_index]
    match = _TITLE_LINE.match(line)
    if match is None:
        return None
    value = match.group("value")
    if not value.endswith("?"):
        return None
    new_value = value[:-1].rstrip()
    if new_value == value:
        return None
    return _replace_title_value(line_index, match, new_value)


def _fix_f001(text: str, diag: Diagnostic) -> TextEdit | None:
    """Sentence-case an ALL CAPS rule title.

    Excludes acronyms shorter than 3 letters (`HTTP`, `JSON` stay
    uppercase if surrounded by lowercase) is **not** attempted —
    F001 only fires on titles dominated by uppercase, so a clean
    `Title-cased Title` is the right output most of the time. The
    user can still tune the title manually if they want acronym
    handling.
    """
    line_index = _find_rule_title_line(text, diag)
    if line_index is None:
        return None
    lines = text.splitlines(keepends=False)
    line = lines[line_index]
    match = _TITLE_LINE.match(line)
    if match is None:
        return None
    value = match.group("value")
    if not value or not value.isupper():
        return None
    # Sentence case: capitalize the first letter, lowercase the rest.
    new_value = value.capitalize()
    if new_value == value:
        return None
    return _replace_title_value(line_index, match, new_value)


def _fix_x001(text: str, diag: Diagnostic) -> TextEdit | None:
    """Strip a leading TODO / FIXME / XXX / HACK marker from a rule title.

    Only matches when the marker is at the **start** of the title.
    A title like ``"Review TODO list"`` is left untouched because
    stripping ``TODO`` mid-sentence would change the meaning.
    """
    line_index = _find_rule_title_line(text, diag)
    if line_index is None:
        return None
    lines = text.splitlines(keepends=False)
    line = lines[line_index]
    match = _TITLE_LINE.match(line)
    if match is None:
        return None
    value = match.group("value")
    stripped = _X001_MARKER_PATTERN.sub("", value, count=1)
    if stripped == value:
        return None
    # Capitalize the first letter of the remaining text.
    if stripped:
        stripped = stripped[0].upper() + stripped[1:]
    return _replace_title_value(line_index, match, stripped)


def _fix_s005(text: str, diag: Diagnostic) -> TextEdit | None:
    """Prepend ``# <title>`` to a SKILL.md body lacking an H1.

    Extracts the YAML ``title`` from the frontmatter, finds the
    closing ``---`` delimiter line, and inserts ``# <title>\\n\\n``
    on the line below. Returns ``None`` when the body already has
    an H1 or when the frontmatter shape can't be recovered.
    """
    _ = diag  # position is body-level; we always anchor at frontmatter close.
    fences = _find_frontmatter_fences(text)
    if fences is None:
        return None
    _open_idx, close_idx = fences
    title = _extract_yaml_title(text, _open_idx, close_idx)
    if title is None:
        return None
    if _body_has_h1(text, close_idx):
        return None

    insert_line = close_idx + 1
    insert_text = f"\n# {title}\n"
    # Insert at start-of-line on the line after the closing fence.
    return TextEdit(
        start_line=insert_line,
        start_column=0,
        end_line=insert_line,
        end_column=0,
        new_text=insert_text,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_rule_title_line(text: str, diag: Diagnostic) -> int | None:
    """Find the index of the ``title = "..."`` line near the diagnostic.

    Diagnostics for rule-scoped diagnostics often land on the
    ``[[rules]]`` header. We scan forward up to 8 lines looking for a
    title line; we bail when we hit a blank line or another section
    header (after the first line).
    """
    position = diag.position
    if position is None:
        return None
    start = max(0, position.line - 1)  # Position.line is 1-indexed
    lines = text.splitlines(keepends=False)
    for offset in range(8):
        idx = start + offset
        if idx >= len(lines):
            return None
        if _TITLE_LINE.match(lines[idx]):
            return idx
        if offset == 0:
            continue
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("["):
            return None
    return None


def _replace_title_value(
    line_index: int,
    match: re.Match[str],
    new_value: str,
) -> TextEdit:
    """Build a TextEdit that replaces the value group with ``new_value``."""
    start_col = match.start("value")
    end_col = match.end("value")
    return TextEdit(
        start_line=line_index,
        start_column=start_col,
        end_line=line_index,
        end_column=end_col,
        new_text=new_value,
    )


_REQUIRED_FENCES = 2


def _find_frontmatter_fences(text: str) -> tuple[int, int] | None:
    """Return (open_line_idx, close_line_idx) of the YAML fences, or None."""
    lines = text.splitlines(keepends=False)
    fence_indices = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if len(fence_indices) < _REQUIRED_FENCES or fence_indices[0] != 0:
        return None
    return fence_indices[0], fence_indices[1]


def _extract_yaml_title(text: str, open_idx: int, close_idx: int) -> str | None:
    """Read ``title:`` from the YAML lines between the fences."""
    lines = text.splitlines(keepends=False)
    for line in lines[open_idx + 1 : close_idx]:
        match = re.match(r"^title\s*:\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None


def _body_has_h1(text: str, close_idx: int) -> bool:
    """Return True when at least one ``# ...`` heading sits below the fence."""
    lines = text.splitlines(keepends=False)
    for line in lines[close_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        # The first non-blank line below the fence either is an H1 or
        # it isn't; later lines don't matter for this check.
        return stripped.startswith("# ")
    return False


__all__ = ["compute_fix"]
