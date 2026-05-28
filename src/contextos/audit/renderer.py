"""Renderers for :class:`AuditReport` — CLI text + JSON shapes."""

from __future__ import annotations

import json

from contextos.audit.cross import AuditReport
from contextos.diagnostics import render_cli_many, render_json_many
from contextos.diagnostics.diagnostic import DiagnosticBag


def render_audit_cli(report: AuditReport, *, color: bool = False) -> str:
    """Render an audit report as human-readable text.

    Sections:
    - One block per file with its diagnostics (rustc-style via the
      existing :func:`render_cli_many`).
    - A ``Cross-artifact`` block listing XA*** diagnostics.
    - A ``Skipped files`` block naming files with no parser yet.
    - A trailing summary with totals per severity.
    """
    parts: list[str] = [f"audit {report.repo_path}"]

    if not report.per_file and not report.cross_artifact and not report.skipped:
        parts.append("")
        parts.append("no recognized agent files found")
        return "\n".join(parts).rstrip() + "\n"

    for path, diagnostics in sorted(report.per_file.items()):
        parts.append("")
        parts.append(f"--- {path}")
        if not diagnostics:
            parts.append("no diagnostics")
            continue
        bag = DiagnosticBag(diagnostics)
        parts.append(render_cli_many(bag, color=color))

    if report.cross_artifact:
        parts.append("")
        parts.append("--- Cross-artifact")
        parts.append(render_cli_many(DiagnosticBag(report.cross_artifact), color=color))

    if report.skipped:
        parts.append("")
        parts.append("--- Skipped files (no parser yet)")
        for entry in report.skipped:
            parts.append(f"  {entry['path']}  [{entry['target']}]  {entry['reason']}")

    parts.append("")
    parts.append(f"summary: {report.total_count()} diagnostic(s)")

    return "\n".join(parts).rstrip() + "\n"


def render_audit_json(report: AuditReport, *, indent: int | None = None) -> str:
    """Render the audit report as JSON.

    Per-file diagnostics use the same :func:`render_json_many` shape as
    individual lint runs (one JSON array of diagnostic objects per file).
    """
    payload = {
        "repo_path": str(report.repo_path),
        "per_file": {
            path: json.loads(render_json_many(DiagnosticBag(diags)))
            for path, diags in sorted(report.per_file.items())
        },
        "cross_artifact": json.loads(render_json_many(DiagnosticBag(report.cross_artifact))),
        "skipped": list(report.skipped),
        "total_count": report.total_count(),
    }
    return json.dumps(payload, indent=indent, sort_keys=True)
