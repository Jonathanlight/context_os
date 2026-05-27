"""Machine-readable JSON output for diagnostics.

Two entry points:

- :func:`render_json` for a single diagnostic
- :func:`render_json_many` for the contents of a bag, sorted

The shape mirrors SPEC.md §3 (one object per diagnostic) so downstream
consumers — CI dashboards, GitHub action annotations, editor integrations
— can deserialize without per-version glue.
"""

from __future__ import annotations

import json
from typing import Any

from contextos.diagnostics.diagnostic import Diagnostic, DiagnosticBag


def render_json(diagnostic: Diagnostic, *, indent: int | None = None) -> str:
    """Render a single diagnostic as a JSON object."""
    return json.dumps(_to_dict(diagnostic), indent=indent, sort_keys=True)


def render_json_many(bag: DiagnosticBag, *, indent: int | None = None) -> str:
    """Render every diagnostic in deterministic order as a JSON array."""
    payload = [_to_dict(d) for d in bag.sorted()]
    return json.dumps(payload, indent=indent, sort_keys=True)


def _to_dict(diagnostic: Diagnostic) -> dict[str, Any]:
    """Flatten a Diagnostic to the shape SPEC.md §3 specifies.

    Specifically: lift ``position.file``, ``position.line``, ``position.column``
    to top-level ``file``/``line``/``column``, dropping fields whose value
    is ``None`` so the JSON stays minimal.
    """
    payload: dict[str, Any] = {
        "code": diagnostic.code,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
    }
    if diagnostic.position is not None:
        pos = diagnostic.position
        if pos.file is not None:
            payload["file"] = pos.file
        payload["line"] = pos.line
        payload["column"] = pos.column
    if diagnostic.suggestion is not None:
        payload["suggestion"] = diagnostic.suggestion
    if diagnostic.doc_url is not None:
        payload["doc_url"] = diagnostic.doc_url
    return payload
