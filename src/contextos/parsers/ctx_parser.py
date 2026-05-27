"""Parser for the ``.ctx`` source format.

A ``.ctx`` file is TOML with embedded Markdown strings inside fields like
``Rule.detail``. This module parses the TOML side and builds a strict-typed
:class:`Document` via Pydantic. Markdown bodies stay as raw strings — they
are tokenized later by the dedicated Markdown parser (Milestone 1.4).

Milestone 1.2a scope:

- :func:`parse_ctx_file` / :func:`parse_ctx_string` public API
- The context family only (``artifacts = ["context"]``). The ``skills`` and
  ``rag`` artifacts are reserved for Phase 5 and Phase 6 respectively.
- :class:`ContextOSParseError` with optional source position and suggestion
- Line positions captured for each ``[[rules]]`` entry, so future analyzers
  can report ``file:line:column`` diagnostics.

Milestone 1.2b will widen error coverage (did-you-mean hints across the
full schema, position tracking on every field).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import tomlkit
from pydantic import ValidationError
from tomlkit.exceptions import TOMLKitError

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

SUPPORTED_ARTIFACTS = frozenset({"context"})
"""Artifact families this parser understands.

Phase 5 will add ``"skills"``, Phase 6 ``"rag"``. Until then we fail loudly
rather than silently dropping unsupported sections.
"""

_RULES_HEADER_RE = re.compile(r"^\s*\[\[\s*rules\s*\]\]\s*(?:#.*)?$", re.MULTILINE)
_STRING_SOURCE = "<string>"


class ContextOSParseError(Exception):
    """Raised when a ``.ctx`` source cannot be parsed.

    Carries an optional :class:`Position` and a free-form suggestion so the
    CLI renderer can produce ``rustc``-style diagnostics in Milestone 1.3.
    """

    def __init__(
        self,
        message: str,
        *,
        source: str | None = None,
        position: Position | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.message = message
        self.source = source
        self.position = position
        self.suggestion = suggestion
        prefix = ""
        if position is not None:
            file = position.file or source or "<unknown>"
            prefix = f"{file}:{position.line}:{position.column}: "
        elif source is not None:
            prefix = f"{source}: "
        full = f"{prefix}{message}"
        if suggestion is not None:
            full = f"{full}\n  hint: {suggestion}"
        super().__init__(full)


def parse_ctx_file(path: Path) -> Document:
    """Parse a ``.ctx`` file from disk into a :class:`Document`.

    Raises :class:`ContextOSParseError` if the file cannot be read or the
    content does not match the schema.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContextOSParseError(f"cannot read file: {exc}", source=str(path)) from exc
    return parse_ctx_string(content, source=str(path))


def parse_ctx_string(content: str, source: str = _STRING_SOURCE) -> Document:
    """Parse a ``.ctx`` source string into a :class:`Document`.

    ``source`` is used purely for error messages; pass the file path for
    on-disk content and leave the default for in-memory snippets.
    """
    try:
        parsed = tomlkit.parse(content)
    except TOMLKitError as exc:
        raise ContextOSParseError(f"invalid TOML: {exc}", source=source) from exc

    data = parsed.unwrap()
    if not isinstance(data, dict):
        raise ContextOSParseError("root must be a TOML table", source=source)

    project = data.get("project")
    if not isinstance(project, str) or not project.strip():
        raise ContextOSParseError(
            "missing or empty required field 'project'",
            source=source,
            suggestion='add `project = "YourProjectName"` at the top',
        )

    artifacts_raw = data.get("artifacts", ["context"])
    if not isinstance(artifacts_raw, list) or not artifacts_raw:
        raise ContextOSParseError(
            "'artifacts' must be a non-empty array of strings",
            source=source,
            suggestion='e.g. artifacts = ["context"]',
        )
    unsupported = [a for a in artifacts_raw if a not in SUPPORTED_ARTIFACTS]
    if unsupported:
        raise ContextOSParseError(
            f"unsupported artifact(s): {unsupported}",
            source=source,
            suggestion=(
                "only 'context' is supported in this release; "
                "'skills' lands in Phase 5, 'rag' in Phase 6"
            ),
        )

    rule_lines = _scan_rule_positions(content)
    agent = _build_agent_document(data, source=source, rule_lines=rule_lines)

    try:
        return Document(
            project=project,
            ctx_version=str(data.get("ctx_version", "0.3")),
            type="agent",
            languages=_string_list(data.get("languages", []), field="languages", source=source),
            authors=_string_list(data.get("authors", []), field="authors", source=source),
            version=str(data.get("version", "0.1.0")),
            agent=agent,
        )
    except ValidationError as exc:
        raise ContextOSParseError(f"document failed validation: {exc}", source=source) from exc


def _scan_rule_positions(content: str) -> list[int]:
    """Return the 1-indexed line of every ``[[rules]]`` header.

    ``tomlkit`` preserves array-of-table order but does not expose line
    numbers cleanly. A regex scan over the raw source maps each ``[[rules]]``
    occurrence to its line, and the order matches the order tomlkit yields.
    """
    return [i + 1 for i, line in enumerate(content.splitlines()) if _RULES_HEADER_RE.match(line)]


def _build_agent_document(
    data: dict[str, Any],
    *,
    source: str,
    rule_lines: list[int],
) -> AgentDocument:
    """Build an :class:`AgentDocument` from the unwrapped root TOML data."""
    return AgentDocument(
        identity=_build_optional(Identity, data.get("identity"), "identity", source),
        stack=_build_optional(Stack, data.get("stack"), "stack", source),
        style=_build_optional(Style, data.get("style"), "style", source),
        tools=_build_optional(Tools, data.get("tools"), "tools", source),
        rules=_build_rules(data.get("rules", []), source=source, rule_lines=rule_lines),
        forbidden_patterns=_string_list(
            data.get("forbidden_patterns", []),
            field="forbidden_patterns",
            source=source,
        ),
    )


def _build_optional(
    model_cls: Any,
    value: Any,
    field: str,
    source: str,
) -> Any:
    """Construct an optional submodel or return None when the section is absent.

    Strict on shape: the section must be a TOML table when present.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContextOSParseError(f"'[{field}]' must be a TOML table", source=source)
    try:
        return model_cls(**value)
    except ValidationError as exc:
        raise ContextOSParseError(f"invalid [{field}] section: {exc}", source=source) from exc


def _build_rules(
    rules_raw: Any,
    *,
    source: str,
    rule_lines: list[int],
) -> list[Rule]:
    """Construct the list of :class:`Rule` from ``[[rules]]`` entries."""
    if not isinstance(rules_raw, list):
        raise ContextOSParseError("'[[rules]]' must be an array of tables", source=source)
    rules: list[Rule] = []
    file_for_pos = source if source != _STRING_SOURCE else None
    for i, entry in enumerate(rules_raw):
        if not isinstance(entry, dict):
            raise ContextOSParseError(
                f"each [[rules]] entry must be a table (entry #{i + 1})",
                source=source,
            )
        line = rule_lines[i] if i < len(rule_lines) else 1
        position = Position(file=file_for_pos, line=line)

        severity_raw = entry.get("severity")
        if severity_raw is None:
            raise ContextOSParseError(
                f"[[rules]] #{i + 1} is missing 'severity'",
                source=source,
                position=position,
                suggestion="add `severity = \"must\"` (or 'should' / 'may')",
            )
        try:
            severity = Severity(severity_raw)
        except ValueError as exc:
            raise ContextOSParseError(
                f"unknown severity '{severity_raw}' in [[rules]] #{i + 1}",
                source=source,
                position=position,
                suggestion="expected one of: must, should, may",
            ) from exc

        kwargs = dict(entry)
        kwargs["severity"] = severity
        kwargs["position"] = position
        try:
            rules.append(Rule(**kwargs))
        except ValidationError as exc:
            raise ContextOSParseError(
                f"invalid [[rules]] entry #{i + 1}: {exc}",
                source=source,
                position=position,
            ) from exc
    return rules


def _string_list(value: Any, *, field: str, source: str) -> list[str]:
    """Validate that ``value`` is a list of strings and return a fresh copy."""
    if not isinstance(value, list):
        raise ContextOSParseError(f"'{field}' must be an array", source=source)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ContextOSParseError(f"'{field}' must contain only strings", source=source)
        out.append(item)
    return out
