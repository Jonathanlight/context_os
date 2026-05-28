"""LSP completion logic for ``.ctx`` and ``SKILL.md`` files.

Kept pure (no pygls runtime import — only ``lsprotocol.types``) so the
unit tests don't need a server fixture. The public entry point is
:func:`compute_completions`, which takes the document text, the cursor
position, and the file URI, and returns a list of LSP completion items
ordered by relevance.

Detection strategy is intentionally simple: a regex-based partial lex
of the current line's prefix. We do **not** spin up the full TOML
parser per keystroke — it would be too slow and would fail more often
than not (the document is half-typed). Instead we recognize a small
set of high-signal patterns and bail to an empty list when the
context isn't clear. That keeps false positives down at the cost of
some recall.
"""

from __future__ import annotations

import re

from lsprotocol import types as lsp

from contextos.ast.common import Severity
from contextos.ast.rag import ChunkingStrategy
from contextos.ast.skill import ExpectedOutputFormat
from contextos.parsers.ctx_parser import KNOWN_ROOT_FIELDS

# ---------------------------------------------------------------------------
# Value enums — derived from the AST literals so a SPEC change ripples here.
# ---------------------------------------------------------------------------

_SEVERITY_VALUES = tuple(s.value for s in Severity)
_CHUNKING_STRATEGIES: tuple[str, ...] = ChunkingStrategy.__args__  # type: ignore[attr-defined]
_OUTPUT_FORMATS: tuple[str, ...] = ExpectedOutputFormat.__args__  # type: ignore[attr-defined]

# Fields whose value is a closed Literal. Map the field name to the
# allowed values so the cursor inside `<field> = "<cursor>"` can suggest
# them directly.
_ENUM_VALUE_FIELDS: dict[str, tuple[str, ...]] = {
    "severity": _SEVERITY_VALUES,
    "chunking_strategy": _CHUNKING_STRATEGIES,
    "chunking_override": _CHUNKING_STRATEGIES,
    "expected_output_format": _OUTPUT_FORMATS,
}

# ---------------------------------------------------------------------------
# Section names — what comes after `[` (table) or `[[` (array-of-tables).
# ---------------------------------------------------------------------------

_TOML_SINGLE_SECTIONS = ("identity", "stack", "style", "tools", "rag")
_TOML_ARRAY_SECTIONS = ("rules", "skill", "document")

# ---------------------------------------------------------------------------
# Skill frontmatter — keys allowed in the YAML header of SKILL.md.
# ---------------------------------------------------------------------------

_SKILL_FRONTMATTER_KEYS = (
    "name",
    "title",
    "description",
    "trigger_keywords",
    "applies_to",
    "languages_supported",
    "files",
    "required_runtime",
    "example_invocation",
    "expected_output_format",
    "tags",
)

# Regex patterns used by the dispatcher. Each is anchored to the
# **prefix** of the current line so the cursor is always at the end.
_LINE_OPEN_DOUBLE_BRACKET = re.compile(r"^\s*\[\[(\w*)$")
_LINE_OPEN_SINGLE_BRACKET = re.compile(r"^\s*\[(\w*)$")
_LINE_KEY_VALUE_OPEN_STRING = re.compile(r'^\s*(?P<field>\w+)\s*=\s*"(?P<value>[^"]*)$')
_LINE_BARE_PREFIX = re.compile(r"^(?P<indent>\s*)(?P<word>\w*)$")
_LINE_YAML_KEY_OPEN = re.compile(r"^(?P<word>\w*)$")


def compute_completions(
    text: str,
    position: lsp.Position,
    uri: str,
) -> list[lsp.CompletionItem]:
    """Top-level dispatcher. Returns LSP completion items or ``[]``.

    Tries the file-type-specific completers in order; the first that
    matches wins. The fallback is an empty list — never an exception,
    never a noisy default that pollutes the editor's suggestion view.
    """
    line = _line_prefix(text, position)
    lowered_uri = uri.lower()

    if lowered_uri.endswith(".ctx"):
        return _complete_ctx(line)
    if lowered_uri.endswith("/skill.md") or lowered_uri.endswith("skill.md"):
        return _complete_skill_frontmatter(text, position, line)
    return []


def _line_prefix(text: str, position: lsp.Position) -> str:
    """Return the portion of the current line before the cursor."""
    lines = text.splitlines()
    if position.line >= len(lines):
        return ""
    return lines[position.line][: position.character]


def _complete_ctx(line: str) -> list[lsp.CompletionItem]:
    """Dispatch the ``.ctx`` patterns in order of specificity."""
    # 1. `[[<word>` — array-of-tables section name.
    match = _LINE_OPEN_DOUBLE_BRACKET.match(line)
    if match is not None:
        return _section_items(_TOML_ARRAY_SECTIONS, prefix=match.group(1), wrap="]]")
    # 2. `[<word>` — single-table section name.
    match = _LINE_OPEN_SINGLE_BRACKET.match(line)
    if match is not None:
        return _section_items(_TOML_SINGLE_SECTIONS, prefix=match.group(1), wrap="]")
    # 3. `<field> = "<value>` — value enum completion.
    match = _LINE_KEY_VALUE_OPEN_STRING.match(line)
    if match is not None:
        allowed = _ENUM_VALUE_FIELDS.get(match.group("field"))
        if allowed is not None:
            return _value_items(allowed, prefix=match.group("value"))
    # 4. Bare prefix at start of line → top-level keys.
    match = _LINE_BARE_PREFIX.match(line)
    if match is not None:
        return _key_items(sorted(KNOWN_ROOT_FIELDS), prefix=match.group("word"))
    return []


def _complete_skill_frontmatter(
    text: str,
    position: lsp.Position,
    line: str,
) -> list[lsp.CompletionItem]:
    """Inside the YAML frontmatter, suggest known SkillDocument keys.

    The frontmatter is the region between the opening ``---`` and the
    closing ``---`` (or end-of-file if the closing delimiter isn't
    typed yet). Outside that region we stay silent so we don't
    pollute Markdown body completion.
    """
    if not _inside_skill_frontmatter(text, position):
        return []
    # Value-enum match wins (e.g. `expected_output_format: <cursor>`).
    enum_match = re.match(r"^(?P<field>\w+):\s*(?P<value>\S*)$", line)
    if enum_match is not None:
        allowed = _ENUM_VALUE_FIELDS.get(enum_match.group("field"))
        if allowed is not None:
            return _value_items(allowed, prefix=enum_match.group("value"))
    # Otherwise, key completion at start of line.
    key_match = _LINE_YAML_KEY_OPEN.match(line)
    if key_match is not None:
        return _key_items(list(_SKILL_FRONTMATTER_KEYS), prefix=key_match.group("word"))
    return []


def _inside_skill_frontmatter(text: str, position: lsp.Position) -> bool:
    """Detect whether the cursor sits between the two ``---`` fences.

    Counts the ``---`` delimiters on lines **before** the cursor. An
    odd count means we're inside the YAML; an even count means we're
    outside (either before the first fence or after the second).
    """
    lines = text.splitlines()
    fences = 0
    for idx, line in enumerate(lines):
        if idx > position.line:
            break
        if line.strip() == "---":
            fences += 1
            if idx == position.line:
                # Cursor is on a fence line — treat as outside so we
                # don't suggest YAML keys on the delimiter itself.
                return False
    return fences % 2 == 1


# ---------------------------------------------------------------------------
# Item builders — keep CompletionItem construction in one place.
# ---------------------------------------------------------------------------


def _section_items(
    names: tuple[str, ...],
    *,
    prefix: str,
    wrap: str,
) -> list[lsp.CompletionItem]:
    """Build completion items for TOML section names."""
    return [
        lsp.CompletionItem(
            label=name,
            kind=lsp.CompletionItemKind.Struct,
            insert_text=f"{name}{wrap}",
            detail=f"TOML section [{name}{wrap[:-1]}]" if wrap == "]" else f"TOML AoT [[{name}]]",
        )
        for name in names
        if name.startswith(prefix)
    ]


def _value_items(values: tuple[str, ...], *, prefix: str) -> list[lsp.CompletionItem]:
    """Build completion items for enum values inside double quotes."""
    return [
        lsp.CompletionItem(
            label=value,
            kind=lsp.CompletionItemKind.EnumMember,
            insert_text=value,
        )
        for value in values
        if value.startswith(prefix)
    ]


def _key_items(keys: list[str], *, prefix: str) -> list[lsp.CompletionItem]:
    """Build completion items for top-level keys / YAML keys."""
    return [
        lsp.CompletionItem(
            label=key,
            kind=lsp.CompletionItemKind.Field,
            insert_text=key,
        )
        for key in keys
        if key.startswith(prefix)
    ]


__all__ = ["compute_completions"]
