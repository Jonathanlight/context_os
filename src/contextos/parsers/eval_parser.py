"""Parser for ``.eval.toml`` files — Phase 7.7.

A ``.eval.toml`` is a TOML source declaring an :class:`EvalSuite`:
the project name, the eval target (which artifact family is being
evaluated), and one or more case blocks (``[[skill_case]]`` or
``[[rag_case]]``).

This parser shares the conventions of :mod:`contextos.parsers.ctx_parser`:
``tomlkit`` for parsing (comments and order preserved on round-trip
when we eventually add a dumper), :class:`ContextOSParseError` for
every failure mode (with ``file:line:column`` positions and concrete
suggestions), and Pydantic for the structural validation that ripples
into the same error type.

The runner that actually invokes an LLM and scores the result lives
in :mod:`contextos.eval` (Phase 7.8 / 7.9). The parser stays
side-effect free.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomlkit
from pydantic import ValidationError
from tomlkit.exceptions import TOMLKitError

from contextos.ast.eval import EvalSuite
from contextos.parsers.ctx_parser import ContextOSParseError

_STRING_SOURCE = "<string>"

_KNOWN_ROOT_FIELDS = frozenset(
    {
        "project",
        "target",
        "suite_version",
        "skill_case",
        "rag_case",
    }
)
"""Top-level keys an eval source may carry.

The case lists are TOML array-of-tables (``[[skill_case]]`` /
``[[rag_case]]``) so they appear at the root under the singular key
name; the parser remaps them into the plural ``skill_cases`` /
``rag_cases`` Pydantic fields before validation.
"""


def parse_eval_file(path: Path) -> EvalSuite:
    """Parse an ``.eval.toml`` file from disk into an :class:`EvalSuite`.

    Raises :class:`ContextOSParseError` on read failure, malformed
    TOML, unknown root field, or schema validation failure.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContextOSParseError(f"cannot read file: {exc}", source=str(path)) from exc
    return parse_eval_string(content, source=str(path))


def parse_eval_string(content: str, source: str = _STRING_SOURCE) -> EvalSuite:
    """Parse an eval source string into an :class:`EvalSuite`.

    ``source`` is the label that appears in diagnostics; pass the
    file path for on-disk content, leave the default for in-memory
    snippets.
    """
    try:
        parsed = tomlkit.parse(content)
    except TOMLKitError as exc:
        raise ContextOSParseError(f"invalid TOML: {exc}", source=source) from exc

    data = parsed.unwrap()
    if not isinstance(data, dict):
        raise ContextOSParseError(
            "root must be a TOML table",
            source=source,
            suggestion="the eval source should declare project / target / case blocks",
        )

    _check_root_fields(data, source=source)

    payload: dict[str, Any] = {
        "project": data.get("project"),
        "target": data.get("target"),
    }
    if "suite_version" in data:
        payload["suite_version"] = data["suite_version"]

    payload["skill_cases"] = _coerce_cases(
        data.get("skill_case", []),
        family="skill_case",
        source=source,
    )
    payload["rag_cases"] = _coerce_cases(
        data.get("rag_case", []),
        family="rag_case",
        source=source,
    )

    try:
        return EvalSuite.model_validate(payload)
    except ValidationError as exc:
        raise ContextOSParseError(
            f"eval suite failed validation: {exc}",
            source=source,
            suggestion=(
                "see SkillCase / RagCase field documentation in "
                "contextos.ast.eval for the expected schema"
            ),
        ) from exc


def _check_root_fields(data: dict[str, Any], *, source: str) -> None:
    """Reject typos at the root level with a did-you-mean hint.

    Mirrors the same shape as the ctx_parser root-field check so
    the user gets a familiar diagnostic when they reach for
    ``project_name`` instead of ``project``.
    """
    unknown = sorted(set(data.keys()) - _KNOWN_ROOT_FIELDS)
    if not unknown:
        return
    msg = f"unknown root field(s): {unknown}"
    suggestion = f"valid root fields: {sorted(_KNOWN_ROOT_FIELDS)}"
    raise ContextOSParseError(msg, source=source, suggestion=suggestion)


def _coerce_cases(
    raw: Any,
    *,
    family: str,
    source: str,
) -> list[dict[str, Any]]:
    """Validate that the raw value is a list of dicts; return as-is.

    Pydantic does the structural validation downstream; this helper
    only catches the shape mismatch (``[skill_case]`` written as a
    single table instead of array-of-tables) so the error message
    can name the offending family.
    """
    if not isinstance(raw, list):
        msg = f"[[{family}]] must be a TOML array-of-tables, not a {type(raw).__name__}"
        suggestion = f"use double brackets: [[{family}]]"
        raise ContextOSParseError(msg, source=source, suggestion=suggestion)
    coerced: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            msg = f"[[{family}]] entry #{index + 1} must be a TOML table"
            raise ContextOSParseError(msg, source=source)
        coerced.append(item)
    return coerced


__all__ = [
    "parse_eval_file",
    "parse_eval_string",
]
