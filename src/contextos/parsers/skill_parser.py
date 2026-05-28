"""Parser for ``SKILL.md`` source files — Phase 5.2.

A ``SKILL.md`` is a Markdown file whose first block is a YAML
frontmatter section delimited by ``---``. The frontmatter declares the
skill's metadata (``name``, ``title``, ``description``, plus the
recommended SPEC §1.3 fields). Everything after the closing ``---``
delimiter is the freeform Markdown body — usage instructions, examples,
references — preserved verbatim on the AST.

This parser deliberately rejects unknown frontmatter keys (Pydantic's
``extra="forbid"`` on :class:`SkillDocument`) so a typo can't masquerade
as a working field. The SPEC field list is the contract; surfaces that
need additional fields (e.g. Anthropic's ``allowed-tools``) extend
:class:`SkillDocument` first.

If the frontmatter omits ``title`` but the body starts with an H1, the
parser derives ``title`` from that heading — a pragmatic bridge so real
Anthropic-flavored ``SKILL.md`` files (which don't carry a ``title``
field) still parse cleanly.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, cast

from mistletoe.block_token import Document as MistletoeDocument
from mistletoe.block_token import Heading
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from contextos.ast.common import Position
from contextos.ast.document import Document
from contextos.ast.skill import SkillDocument
from contextos.parsers.ctx_parser import ContextOSParseError

_FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\n(?:(?P<frontmatter>.*?)\n)?---[ \t]*(?:\n(?P<body>.*))?\Z",
    re.DOTALL,
)
"""Match ``---`` + YAML + ``---`` + optional body. ``\\A``/``\\Z`` anchor
to the start/end of the whole string so a stray ``---`` mid-file cannot
be mistaken for the frontmatter delimiter."""

_STRING_SOURCE = "<string>"


def _yaml_loader() -> YAML:
    """Build a fresh safe YAML loader.

    ``typ="safe"`` blocks the constructor that would otherwise let
    crafted YAML instantiate arbitrary Python objects. We rebuild per
    call rather than caching a module-level singleton because the
    loader carries mutable parser state.
    """
    return YAML(typ="safe")


def parse_skill_file(path: Path) -> Document:
    """Parse a ``SKILL.md`` file from disk into a :class:`Document`.

    Raises:
        ContextOSParseError: when the file is unreadable, the frontmatter
            is malformed, a required field is missing, or an unknown key
            appears in the YAML.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContextOSParseError(f"cannot read file: {exc}", source=str(path)) from exc
    return parse_skill_string(content, source=str(path))


def parse_skill_string(content: str, source: str = _STRING_SOURCE) -> Document:
    """Parse a ``SKILL.md`` source string into a :class:`Document`.

    ``source`` is used purely for diagnostics; pass the file path for
    on-disk content and leave the default for in-memory snippets.
    """
    match = _FRONTMATTER_PATTERN.match(content)
    if match is None:
        raise ContextOSParseError(
            "SKILL.md is missing the YAML frontmatter block",
            source=source,
            position=Position(file=source, line=1, column=1),
            suggestion=(
                "wrap the metadata at the top of the file in a '---'-"
                "delimited YAML block, e.g.\n"
                "    ---\n    name: my-skill\n    description: ...\n    ---"
            ),
        )

    yaml_text = match.group("frontmatter") or ""
    body = match.group("body") or ""

    data = _load_frontmatter(yaml_text, source=source)
    _ensure_title(data, body=body)
    data["body"] = body

    skill = _build_skill_document(data, source=source)
    return Document(project=skill.name, type="skill", skill=skill)


def _load_frontmatter(yaml_text: str, *, source: str) -> dict[str, Any]:
    """Parse the YAML frontmatter into a dict, surfacing YAML errors.

    The frontmatter must be a mapping at the top level; YAML sequences
    or scalars are rejected with a pointer at line 2 (the first content
    line of the frontmatter block).
    """
    loader = _yaml_loader()
    try:
        data = loader.load(io.StringIO(yaml_text))
    except YAMLError as exc:
        line, column = _yaml_position(exc)
        raise ContextOSParseError(
            f"invalid YAML frontmatter: {exc}",
            source=source,
            position=Position(file=source, line=line + 1, column=column),
            suggestion="check indentation and quoting in the '---' block",
        ) from exc

    if data is None:
        raise ContextOSParseError(
            "SKILL.md frontmatter is empty",
            source=source,
            position=Position(file=source, line=2, column=1),
            suggestion="add at minimum `name:` and `description:` keys",
        )
    if not isinstance(data, dict):
        raise ContextOSParseError(
            "SKILL.md frontmatter must be a YAML mapping",
            source=source,
            position=Position(file=source, line=2, column=1),
            suggestion="declare key/value pairs, not a list or scalar",
        )
    return cast(dict[str, Any], data)


def _yaml_position(exc: YAMLError) -> tuple[int, int]:
    """Best-effort extraction of line/column from a ruamel.yaml error.

    Falls back to (0, 1) when the error doesn't carry a marker (e.g.
    composer errors raised without a Mark attached).
    """
    mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
    if mark is None:
        return 0, 1
    return int(mark.line), int(mark.column) + 1


def _ensure_title(data: dict[str, Any], *, body: str) -> None:
    """Backfill ``title`` from the body's first H1 when the YAML omits it.

    Anthropic's real-world ``SKILL.md`` files don't carry a ``title``
    field — the document title lives in an H1 at the top of the body.
    SPEC §1.3 requires the AST node to expose ``title``, so we bridge
    the gap by reading the first H1 we can find. The YAML value always
    wins when both are present.
    """
    if data.get("title"):
        return
    h1 = _first_h1(body)
    if h1 is not None:
        data["title"] = h1


def _first_h1(body: str) -> str | None:
    """Return the text of the first H1 in ``body``, or None if absent.

    Uses mistletoe so atx-style (``# ...``) and setext-style
    (``...\\n====``) headings both work, and so we don't get fooled by
    ``#`` characters inside code fences.
    """
    if not body.strip():
        return None
    md = MistletoeDocument(body.splitlines(keepends=True))
    for child in md.children or ():
        if isinstance(child, Heading) and child.level == 1:
            return _flatten_inline(child)
    return None


def _flatten_inline(node: object) -> str:
    """Concatenate the raw text of every inline node under ``node``.

    Mistletoe's block-level nodes (Heading, Paragraph, …) carry both
    ``content`` (the raw Markdown source, with ``**`` / ``_`` markers
    intact) and ``children`` (the parsed inline tree). We always prefer
    ``children`` so formatting marks are stripped; ``content`` is the
    leaf fallback for RawText nodes where no further children exist.
    """
    children = getattr(node, "children", None)
    if children:
        return "".join(_flatten_inline(child) for child in children)
    content = getattr(node, "content", None)
    return content if isinstance(content, str) else ""


def _build_skill_document(data: dict[str, Any], *, source: str) -> SkillDocument:
    """Run the dict through :class:`SkillDocument`, mapping errors back.

    Pydantic's :class:`ValidationError` lists every offending field;
    we surface them all in a single :class:`ContextOSParseError`
    message so the CLI prints one diagnostic block per file.
    """
    try:
        return SkillDocument.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ContextOSParseError(
            f"SKILL.md frontmatter failed validation: {details}",
            source=source,
            position=Position(file=source, line=2, column=1),
            suggestion=(
                "consult docs/specs/SPEC.md §1.3 for the complete field list and required types"
            ),
        ) from exc


__all__ = [
    "parse_skill_file",
    "parse_skill_string",
]
