"""Generic Markdown parser for existing agent context files.

Reads a Markdown source (``CLAUDE.md``, ``AGENTS.md``, ``.cursorrules``, …)
and produces a :class:`Document` by matching H2 headings against the
target's alias table, then extracting list items as :class:`Rule`s and
table-shape sections (stack, tools) by their sub-headings.

The per-target mapping lives in ``targets/mappings/<target>.toml``. Adding
a new target is just dropping a TOML file — no code change.

Milestone 1.4 ships the ``claude_code`` mapping. Phase 3 adds codex,
cursor, copilot, cline, windsurf.

Note on mapping format: phase1_todo.md mentioned YAML, but adding PyYAML
just for an internal mapping file means a new dependency that requires
explicit approval per CLAUDE.md. TOML reads via ``tomllib`` (stdlib in
Python 3.11+), zero deps, and keeps the project's TOML-first ethos
consistent with ``.ctx``. PyYAML will land when Phase 6 RAG configs need
it; the mapping format can migrate then or stay TOML.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from mistletoe import block_token, span_token
from mistletoe.block_token import Document as MistletoeDocument

from contextos.ast.agent import (
    AgentDocument,
    Identity,
    Rule,
    Stack,
    Style,
    Tools,
)
from contextos.ast.common import Position, Severity
from contextos.ast.document import Document
from contextos.parsers.ctx_parser import ContextOSParseError

MAPPINGS_DIR = Path(__file__).resolve().parent / "targets" / "mappings"
SUPPORTED_TARGETS = ("claude_code",)
_GENERATED_RULE_PREFIX = "MD"
_STRING_SOURCE = "<string>"
_H2 = 2
_H3 = 3


def parse_markdown_file(path: Path, target: str) -> Document:
    """Parse a Markdown file into a Document using a target mapping."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContextOSParseError(f"cannot read file: {exc}", source=str(path)) from exc
    return parse_markdown_string(content, target, source=str(path))


def parse_markdown_string(
    content: str,
    target: str,
    source: str = _STRING_SOURCE,
) -> Document:
    """Parse a Markdown source string into a Document."""
    mapping = _load_mapping(target, source=source)

    ast = MistletoeDocument(content.splitlines(keepends=True))
    project = _extract_project_name(ast) or _project_from_source(source)
    sections = _partition_by_h2(ast, mapping=mapping)
    agent = _build_agent_document(
        sections,
        mapping=mapping,
        source=source,
    )
    return Document(project=project, type="agent", agent=agent)


def _load_mapping(target: str, *, source: str) -> dict[str, Any]:
    """Read the target's TOML mapping. Raises if the target is unknown."""
    if target not in SUPPORTED_TARGETS:
        raise ContextOSParseError(
            f"unsupported target '{target}'",
            source=source,
            suggestion=f"supported targets: {', '.join(SUPPORTED_TARGETS)}",
        )
    path = MAPPINGS_DIR / f"{target}.toml"
    if not path.is_file():
        raise ContextOSParseError(
            f"missing target mapping: {path}",
            source=source,
        )
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _project_from_source(source: str) -> str:
    """Default project name when no H1 is present: filename stem or 'Unknown'."""
    if source == _STRING_SOURCE:
        return "Unknown"
    return Path(source).stem or "Unknown"


def _extract_project_name(ast: block_token.Document) -> str | None:
    """Return the text of the first H1 if present."""
    children = ast.children or []
    for child in children:
        if isinstance(child, block_token.Heading) and child.level == 1:
            return _text_of(child.children).strip() or None
        if isinstance(child, block_token.Heading):
            break  # the first heading is not H1; stop looking
    return None


def _partition_by_h2(
    ast: block_token.Document,
    *,
    mapping: dict[str, Any],
) -> dict[str, list[Any]]:
    """Split the document body into named buckets keyed by canonical section name.

    A bucket holds the block tokens between its opening H2 and the next H2.
    Unrecognized H2 sections are dropped — Milestone 1.5 will fold them back
    in as ProseBlocks if round-trip stability requires it.
    """
    section_lookup = _build_alias_lookup(mapping)
    buckets: dict[str, list[Any]] = {}
    current: str | None = None

    for child in ast.children or []:
        if isinstance(child, block_token.Heading) and child.level == _H2:
            title = _text_of(child.children).strip()
            current = section_lookup.get(_norm_title(title))
            continue
        if current is not None:
            buckets.setdefault(current, []).append(child)
    return buckets


def _build_alias_lookup(mapping: dict[str, Any]) -> dict[str, str]:
    """Pre-compute lowercased alias → canonical section name."""
    lookup: dict[str, str] = {}
    for section_name, section_cfg in mapping.get("sections", {}).items():
        for alias in section_cfg.get("aliases", []):
            lookup[_norm_title(alias)] = section_name
    return lookup


def _build_agent_document(
    sections: dict[str, list[Any]],
    *,
    mapping: dict[str, Any],
    source: str,
) -> AgentDocument:
    """Build the AgentDocument from partitioned section blocks."""
    return AgentDocument(
        identity=_extract_identity(sections.get("identity", [])),
        stack=_extract_stack(sections.get("stack", []), mapping=mapping),
        style=_extract_style(sections.get("style", [])),
        tools=_extract_tools(sections.get("tools", []), mapping=mapping),
        rules=_extract_rules(
            sections.get("rules", []),
            severity_keywords=mapping.get("severity_keywords", {}),
            source=source,
        ),
        forbidden_patterns=_collect_bullet_items(sections.get("forbidden_patterns", [])),
    )


def _extract_identity(blocks: list[Any]) -> Identity | None:
    """First non-empty paragraph in the Identity section becomes role."""
    role = _first_paragraph_text(blocks)
    if role is None:
        return None
    return Identity(role=role)


def _extract_stack(blocks: list[Any], *, mapping: dict[str, Any]) -> Stack | None:
    """Stack supports H3 sub-sections (required / forbidden / preferred).

    If no sub-sections are present, the bullet list at the top of the
    section is treated as the ``required`` bucket.
    """
    sub_map = mapping.get("sections", {}).get("stack", {}).get("sub_sections", {})
    buckets = _partition_by_h3(blocks, sub_map)
    required = _collect_bullet_items(buckets.get("required", []))
    forbidden = _collect_bullet_items(buckets.get("forbidden", []))
    preferred = _collect_bullet_items(buckets.get("preferred", []))
    if not buckets and blocks:
        # No H3 sub-sections — collect everything as required.
        required = _collect_bullet_items(blocks)
    if not (required or forbidden or preferred):
        return None
    return Stack(required=required, forbidden=forbidden, preferred=preferred)


def _extract_style(blocks: list[Any]) -> Style | None:
    items = _collect_bullet_items(blocks)
    if not items:
        return None
    return Style(conventions=items)


def _extract_tools(blocks: list[Any], *, mapping: dict[str, Any]) -> Tools | None:
    """Tools section: same sub-section logic as stack (required/forbidden)."""
    sub_map = mapping.get("sections", {}).get("tools", {}).get("sub_sections", {})
    buckets = _partition_by_h3(blocks, sub_map)
    required = _collect_bullet_items(buckets.get("required", []))
    forbidden = _collect_bullet_items(buckets.get("forbidden", []))
    if not buckets and blocks:
        required = _collect_bullet_items(blocks)
    if not (required or forbidden):
        return None
    return Tools(required=required, forbidden=forbidden)


def _extract_rules(
    blocks: list[Any],
    *,
    severity_keywords: dict[str, list[str]],
    source: str,
) -> list[Rule]:
    """Each bullet item in the Rules section becomes a Rule with inferred severity."""
    items = _collect_bullet_items(blocks)
    file_for_pos = source if source != _STRING_SOURCE else None
    rules: list[Rule] = []
    for index, text in enumerate(items, start=1):
        rule_id = f"{_GENERATED_RULE_PREFIX}-{index:03d}"
        severity = _infer_severity(text, severity_keywords)
        rules.append(
            Rule(
                id=rule_id,
                title=text,
                severity=severity,
                position=Position(file=file_for_pos, line=1),
            )
        )
    return rules


def _partition_by_h3(
    blocks: list[Any],
    sub_map: dict[str, list[str]],
) -> dict[str, list[Any]]:
    """Within an H2 section, partition by H3 according to ``sub_map``."""
    lookup: dict[str, str] = {
        _norm_title(alias): canonical for canonical, aliases in sub_map.items() for alias in aliases
    }
    buckets: dict[str, list[Any]] = {}
    current: str | None = None
    for child in blocks:
        if isinstance(child, block_token.Heading) and child.level == _H3:
            title = _text_of(child.children).strip()
            current = lookup.get(_norm_title(title))
            continue
        if current is not None:
            buckets.setdefault(current, []).append(child)
    return buckets


def _collect_bullet_items(blocks: list[Any]) -> list[str]:
    """Walk an H2 section's blocks and pull every bullet item text out.

    Sub-lists are flattened: a nested item still contributes one entry.
    Numbered lists count too. Empty / whitespace items are dropped.
    """
    items: list[str] = []
    for block in blocks:
        if isinstance(block, block_token.List):
            _walk_list(block, items)
    return items


def _walk_list(token: block_token.List, accumulator: list[str]) -> None:
    for item in token.children or []:
        if not isinstance(item, block_token.ListItem):
            continue
        # ListItem contains block tokens; the first paragraph is the bullet
        # text, nested Lists become recursive entries.
        for child in item.children or []:
            if isinstance(child, block_token.Paragraph):
                text = _text_of(child.children).strip()
                if text:
                    accumulator.append(text)
            elif isinstance(child, block_token.List):
                _walk_list(child, accumulator)


def _first_paragraph_text(blocks: list[Any]) -> str | None:
    for block in blocks:
        if isinstance(block, block_token.Paragraph):
            text = _text_of(block.children).strip()
            if text:
                return text
    return None


def _infer_severity(text: str, severity_keywords: dict[str, list[str]]) -> Severity:
    """Match the first ~4 lowercased leading words against severity keywords."""
    leading = " ".join(text.lower().split()[:4])
    for severity_name in ("must", "should", "may"):
        for keyword in severity_keywords.get(severity_name, []):
            if leading.startswith(keyword.lower()):
                return Severity(severity_name)
    return Severity.MUST  # default: most rules in agent context are imperative


def _text_of(tokens: Iterable[Any] | None) -> str:
    """Recursively concatenate the textual content of a span-token tree."""
    if tokens is None:
        return ""
    parts: list[str] = []
    for token in tokens:
        if isinstance(token, span_token.RawText):
            parts.append(token.content)
        elif hasattr(token, "children"):
            children = cast(Iterable[Any] | None, token.children)
            parts.append(_text_of(children))
    return "".join(parts)


def _norm_title(title: str) -> str:
    """Lowercase + collapse internal whitespace, used for alias matching."""
    return " ".join(title.lower().split())
