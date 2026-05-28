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

import difflib
import re
from pathlib import Path
from typing import Any

import tomlkit
from pydantic import BaseModel, ValidationError
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
from contextos.ast.rag import DocumentEntry, RagConfig, RagDocument
from contextos.ast.skill import SkillDocument

SUPPORTED_ARTIFACTS = frozenset({"context", "skills", "rag"})
"""Artifact families this parser understands.

Phase 5.5 added ``"skills"``; Phase 6.2 adds ``"rag"`` so a single
``.ctx`` source can declare a RAG corpus (one ``[rag]`` table plus
one or more ``[[document]]`` entries).
"""

KNOWN_ROOT_FIELDS = frozenset(
    {
        "project",
        "ctx_version",
        "artifacts",
        "languages",
        "authors",
        "targets",
        "version",
        "identity",
        "stack",
        "style",
        "tools",
        "rules",
        "forbidden_patterns",
        "skill",
        "rag",
        "document",
    }
)
"""Every root-level key a ``.ctx`` source may carry in the context family.

Used by :func:`parse_ctx_string` to surface ``did-you-mean`` hints when an
author typos a top-level field. Sub-section field names live on the
Pydantic models themselves and are extracted via ``model_fields`` at error
time.
"""

_RULES_HEADER_RE = re.compile(r"^\s*\[\[\s*rules\s*\]\]\s*(?:#.*)?$", re.MULTILINE)
_STRING_SOURCE = "<string>"
_DID_YOU_MEAN_CUTOFF = 0.6
_DID_YOU_MEAN_LIMIT = 1


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

    _check_root_field_names(data, source=source)

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
                "supported artifacts in this release: 'context', 'skills'; 'rag' lands in Phase 6"
            ),
        )

    if "skills" in artifacts_raw:
        return _build_skill_root(
            data,
            project=project,
            source=source,
        )

    if "rag" in artifacts_raw:
        return _build_rag_root(
            data,
            project=project,
            source=source,
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


def _build_skill_root(
    data: dict[str, Any],
    *,
    project: str,
    source: str,
) -> Document:
    """Build a Document(type='skill') from a ``.ctx`` carrying ``[[skill]]``.

    SPEC §1.3 prescribes ``[[skill]]`` as an array-of-tables; Phase 5.5
    supports a single block per source file. Multi-skill sources will
    arrive with the ``multi`` artifact family — for now they fail loudly.
    """
    skill_blocks = data.get("skill")
    if not isinstance(skill_blocks, list) or not skill_blocks:
        raise ContextOSParseError(
            "artifacts=['skills'] requires at least one [[skill]] block",
            source=source,
            suggestion="add a [[skill]] table with name / title / description",
        )
    if len(skill_blocks) > 1:
        raise ContextOSParseError(
            "multiple [[skill]] blocks in one .ctx file are not yet supported",
            source=source,
            suggestion="split each skill into its own .ctx file for now",
        )
    block = skill_blocks[0]
    if not isinstance(block, dict):
        raise ContextOSParseError(
            "[[skill]] block must be a TOML table",
            source=source,
        )
    try:
        skill = SkillDocument.model_validate(block)
    except ValidationError as exc:
        raise ContextOSParseError(
            f"[[skill]] failed validation: {exc}",
            source=source,
        ) from exc

    try:
        return Document(
            project=project,
            ctx_version=str(data.get("ctx_version", "0.3")),
            type="skill",
            languages=_string_list(data.get("languages", []), field="languages", source=source),
            authors=_string_list(data.get("authors", []), field="authors", source=source),
            version=str(data.get("version", "0.1.0")),
            skill=skill,
        )
    except ValidationError as exc:
        raise ContextOSParseError(f"document failed validation: {exc}", source=source) from exc


def _build_rag_root(
    data: dict[str, Any],
    *,
    project: str,
    source: str,
) -> Document:
    """Build a Document(type='rag') from a ``.ctx`` carrying ``[rag]``.

    SPEC §1.4 prescribes one ``[rag]`` table (the pipeline config) and
    one or more ``[[document]]`` array-of-tables entries (the sources
    to index). A RAG ``.ctx`` without either is structurally complete
    but useless; we surface that as a parse error so the author
    notices at compile time.
    """
    rag_table = data.get("rag")
    if not isinstance(rag_table, dict):
        raise ContextOSParseError(
            "artifacts=['rag'] requires a [rag] table",
            source=source,
            suggestion=(
                "add a [rag] table with at least chunking_strategy and chunk_target_tokens"
            ),
        )

    document_blocks = data.get("document", [])
    if not isinstance(document_blocks, list):
        raise ContextOSParseError(
            "[[document]] must be a TOML array-of-tables",
            source=source,
            suggestion="declare each source as `[[document]]` not `[document]`",
        )
    if not document_blocks:
        raise ContextOSParseError(
            "RAG corpus has no [[document]] entries — nothing would be indexed",
            source=source,
            suggestion=("add at least one [[document]] block declaring a source glob"),
        )

    try:
        config = RagConfig.model_validate(rag_table)
    except ValidationError as exc:
        raise ContextOSParseError(
            f"[rag] failed validation: {exc}",
            source=source,
        ) from exc

    entries: list[DocumentEntry] = []
    for index, block in enumerate(document_blocks):
        if not isinstance(block, dict):
            raise ContextOSParseError(
                f"[[document]] block #{index + 1} must be a TOML table",
                source=source,
            )
        try:
            entries.append(DocumentEntry.model_validate(block))
        except ValidationError as exc:
            raise ContextOSParseError(
                f"[[document]] block #{index + 1} failed validation: {exc}",
                source=source,
            ) from exc

    try:
        return Document(
            project=project,
            ctx_version=str(data.get("ctx_version", "0.3")),
            type="rag",
            languages=_string_list(data.get("languages", []), field="languages", source=source),
            authors=_string_list(data.get("authors", []), field="authors", source=source),
            version=str(data.get("version", "0.1.0")),
            rag=RagDocument(config=config, documents=entries),
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
    model_cls: type[BaseModel],
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
        message, suggestion = _format_validation_error(exc, model_cls=model_cls, section=field)
        raise ContextOSParseError(message, source=source, suggestion=suggestion) from exc


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
            message, suggestion = _format_validation_error(
                exc, model_cls=Rule, section=f"[[rules]] entry #{i + 1}"
            )
            raise ContextOSParseError(
                message,
                source=source,
                position=position,
                suggestion=suggestion,
            ) from exc
    return rules


def _string_list(value: Any, *, field: str, source: str) -> list[str]:
    """Validate that ``value`` is a list of strings and return a fresh copy."""
    if not isinstance(value, list):
        raise ContextOSParseError(
            f"'{field}' must be an array, got {_type_name(value)}",
            source=source,
        )
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ContextOSParseError(
                f"'{field}' must contain only strings; found {_type_name(item)} entry",
                source=source,
            )
        out.append(item)
    return out


def _check_root_field_names(data: dict[str, Any], *, source: str) -> None:
    """Raise if a root-level key is not in :data:`KNOWN_ROOT_FIELDS`.

    Catches typos like ``projct`` or ``rulez`` at the earliest opportunity,
    before Pydantic's per-field validators run.
    """
    for key in data:
        if key in KNOWN_ROOT_FIELDS:
            continue
        suggestion = _did_you_mean(key, KNOWN_ROOT_FIELDS)
        raise ContextOSParseError(
            f"unknown root field '{key}'",
            source=source,
            suggestion=suggestion,
        )


def _format_validation_error(
    exc: ValidationError,
    *,
    model_cls: type[BaseModel],
    section: str,
) -> tuple[str, str | None]:
    """Turn a Pydantic ValidationError into ``(message, suggestion)``.

    Handles three common cases with friendly messages:

    - ``extra_forbidden`` → ``unknown field 'foo'`` + did-you-mean hint
    - ``string_type`` / ``list_type`` / ``int_type`` → wrong type
    - anything else → the verbatim Pydantic message

    Multiple Pydantic errors collapse to the first one; the others surface
    via the original exception's ``__cause__`` chain.
    """
    errors = exc.errors()
    if not errors:
        return f"invalid {section}: {exc}", None

    err = errors[0]
    loc = err.get("loc", ())
    err_type = err.get("type", "")
    field = loc[0] if loc else "?"

    if err_type == "extra_forbidden":
        valid = set(model_cls.model_fields.keys())
        hint = _did_you_mean(str(field), valid)
        return f"unknown field '{field}' in {section}", hint

    if err_type.endswith("_type"):
        expected = err_type.removesuffix("_type")
        got = _type_name(err.get("input"))
        return (
            f"field '{field}' in {section} expected {expected}, got {got}",
            None,
        )

    if err_type == "missing":
        return (
            f"field '{field}' is required in {section}",
            f"add `{field} = ...`",
        )

    return f"invalid {section}: {err.get('msg', exc)}", None


def _did_you_mean(unknown: str, candidates: frozenset[str] | set[str]) -> str | None:
    """Return a ``did you mean 'X'?`` hint via :mod:`difflib`, or None."""
    matches = difflib.get_close_matches(
        unknown,
        candidates,
        n=_DID_YOU_MEAN_LIMIT,
        cutoff=_DID_YOU_MEAN_CUTOFF,
    )
    if matches:
        return f"did you mean '{matches[0]}'?"
    return None


def _type_name(value: Any) -> str:
    """Human-readable name for a value's Python type.

    Used in error messages — TOML-flavored ("array", "table") rather than
    Python-flavored ("list", "dict") since users author TOML, not Python.
    """
    # Order matters: bool is a subclass of int, so it must be checked first.
    if value is None:
        return "null"
    type_map: tuple[tuple[type, str], ...] = (
        (bool, "bool"),
        (int, "int"),
        (float, "float"),
        (str, "str"),
        (list, "array"),
        (dict, "table"),
    )
    for cls, name in type_map:
        if isinstance(value, cls):
            return name
    return type(value).__name__


def dump_ctx_string(doc: Document) -> str:
    """Serialize a :class:`Document` back to canonical ``.ctx`` TOML.

    Output is **semantically** equivalent to whatever produced ``doc`` — not
    necessarily byte-identical (comments and original whitespace are not
    preserved here). Byte-stable emission is a Milestone 1.5 goal for the
    Markdown emitter; the TOML side only commits to round-tripping the AST.

    Used by the round-trip test in Milestone 1.2b and as a building block
    for ``ctx parse … --to-ctx`` (Milestone 1.7 CLI).
    """
    td = tomlkit.document()
    td["project"] = doc.project
    if doc.ctx_version != "0.3":
        td["ctx_version"] = doc.ctx_version
    td["artifacts"] = _artifacts_for_type(doc.type)
    if doc.languages:
        td["languages"] = list(doc.languages)
    if doc.authors:
        td["authors"] = list(doc.authors)
    if doc.version != "0.1.0":
        td["version"] = doc.version

    if doc.type == "skill" and doc.skill is not None:
        td["skill"] = _dump_skill_aot(doc.skill)
        return tomlkit.dumps(td)

    if doc.type == "rag" and doc.rag is not None:
        _dump_rag_into(td, doc.rag)
        return tomlkit.dumps(td)

    if doc.agent is not None:
        _dump_agent_into(td, doc.agent)

    return tomlkit.dumps(td)


def _artifacts_for_type(doc_type: str) -> list[str]:
    """Map :attr:`Document.type` to the canonical ``artifacts`` list.

    Inverse of the dispatch in :func:`parse_ctx_string`. Keeping the
    mapping in one place means a future family addition is a one-line
    table change.
    """
    return {
        "agent": ["context"],
        "skill": ["skills"],
        "rag": ["rag"],
    }[doc_type]


def _dump_agent_into(td: Any, agent: AgentDocument) -> None:
    """Populate ``td`` with the AgentDocument's optional sections.

    Extracted out of :func:`dump_ctx_string` to keep that function's
    branch count under the ruff PLR0912 ceiling; the conditional
    structure here mirrors the skill counterpart for symmetry.
    """
    if agent.forbidden_patterns:
        td["forbidden_patterns"] = list(agent.forbidden_patterns)

    if agent.identity is not None:
        td["identity"] = _dump_optional_table(
            {
                "role": agent.identity.role,
                "context": agent.identity.context,
                "author": agent.identity.author,
            }
        )

    if agent.stack is not None and (
        agent.stack.required or agent.stack.forbidden or agent.stack.preferred
    ):
        td["stack"] = _dump_optional_table(
            {
                "required": agent.stack.required or None,
                "forbidden": agent.stack.forbidden or None,
                "preferred": agent.stack.preferred or None,
            }
        )

    if agent.style is not None and agent.style.conventions:
        td["style"] = _dump_optional_table({"conventions": agent.style.conventions})

    if agent.tools is not None and (agent.tools.required or agent.tools.forbidden):
        td["tools"] = _dump_optional_table(
            {
                "required": agent.tools.required or None,
                "forbidden": agent.tools.forbidden or None,
            }
        )

    if agent.rules:
        rules_aot = tomlkit.aot()
        for rule in agent.rules:
            rules_aot.append(_dump_rule(rule))
        td["rules"] = rules_aot


def _dump_skill_aot(skill: SkillDocument) -> Any:
    """Serialize a :class:`SkillDocument` as a tomlkit array-of-tables.

    SPEC §1.3 prescribes ``[[skill]]``; we emit the single entry as a
    one-element AoT so the canonical form (a top-level array) matches
    what the parser expects on the round-trip.
    """
    aot = tomlkit.aot()
    table = tomlkit.table()
    table["name"] = skill.name
    table["title"] = skill.title
    table["description"] = skill.description
    if skill.trigger_keywords:
        table["trigger_keywords"] = list(skill.trigger_keywords)
    if skill.applies_to:
        table["applies_to"] = list(skill.applies_to)
    if skill.languages_supported:
        table["languages_supported"] = list(skill.languages_supported)
    if skill.files:
        table["files"] = list(skill.files)
    if skill.required_runtime is not None:
        table["required_runtime"] = skill.required_runtime
    if skill.example_invocation is not None:
        table["example_invocation"] = skill.example_invocation
    if skill.expected_output_format is not None:
        table["expected_output_format"] = skill.expected_output_format
    if skill.tags:
        table["tags"] = list(skill.tags)
    aot.append(table)
    return aot


def _dump_rag_into(td: Any, rag: RagDocument) -> None:
    """Populate ``td`` with the RagDocument's [rag] table and [[document]] AoT.

    The config fields land in a non-default-aware way for the always-
    present chunk and top-k numbers: every Pydantic default is emitted
    so the dumped TOML is self-describing rather than depending on a
    future SPEC default that may shift.
    """
    td["rag"] = _dump_rag_config(rag.config)
    if rag.documents:
        doc_aot = tomlkit.aot()
        for entry in rag.documents:
            doc_aot.append(_dump_document_entry(entry))
        td["document"] = doc_aot


def _dump_rag_config(cfg: RagConfig) -> Any:
    table = tomlkit.table()
    table["chunking_strategy"] = cfg.chunking_strategy
    table["chunk_target_tokens"] = cfg.chunk_target_tokens
    table["chunk_overlap_tokens"] = cfg.chunk_overlap_tokens
    table["chunk_min_tokens"] = cfg.chunk_min_tokens
    table["chunk_max_tokens"] = cfg.chunk_max_tokens
    if cfg.embedding_model is not None:
        table["embedding_model"] = cfg.embedding_model
    if cfg.embedding_dimensions is not None:
        table["embedding_dimensions"] = cfg.embedding_dimensions
    if cfg.vector_store is not None:
        table["vector_store"] = cfg.vector_store
    if cfg.reranker is not None:
        table["reranker"] = cfg.reranker
    table["retrieval_top_k"] = cfg.retrieval_top_k
    table["reranking_top_k"] = cfg.reranking_top_k
    if cfg.freshness_policy is not None:
        table["freshness_policy"] = cfg.freshness_policy
    if cfg.language_default is not None:
        table["language_default"] = cfg.language_default
    return table


def _dump_document_entry(entry: DocumentEntry) -> Any:
    table = tomlkit.table()
    table["source"] = entry.source
    if entry.tags:
        table["tags"] = list(entry.tags)
    if entry.freshness_required is not None:
        table["freshness_required"] = entry.freshness_required
    if entry.chunking_override is not None:
        table["chunking_override"] = entry.chunking_override
    if entry.required_anchors:
        table["required_anchors"] = list(entry.required_anchors)
    if entry.max_size_kb is not None:
        table["max_size_kb"] = entry.max_size_kb
    if entry.language is not None:
        table["language"] = entry.language
    return table


def _dump_optional_table(fields: dict[str, Any]) -> Any:
    """Build a tomlkit table dropping keys whose value is ``None`` or empty."""
    table = tomlkit.table()
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            table[key] = list(value)
        else:
            table[key] = value
    return table


def _dump_rule(rule: Rule) -> Any:
    """Serialize a single :class:`Rule` as a tomlkit table for AoT emission."""
    table = tomlkit.table()
    table["id"] = rule.id
    table["title"] = rule.title
    table["severity"] = rule.severity.value
    if rule.applies_to:
        table["applies_to"] = list(rule.applies_to)
    if rule.rationale is not None:
        table["rationale"] = rule.rationale
    if rule.detail is not None:
        table["detail"] = rule.detail
    if rule.example_good is not None:
        table["example_good"] = rule.example_good
    if rule.example_bad is not None:
        table["example_bad"] = rule.example_bad
    if rule.tags:
        table["tags"] = list(rule.tags)
    if rule.links:
        table["links"] = list(rule.links)
    return table
