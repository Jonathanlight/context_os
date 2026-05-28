"""HTML audit report — Phase 8.3.

Hand-rolled HTML renderer for :class:`AuditReport`. No templating
engine (no jinja2 dep); strings are escaped via :func:`html.escape`
at every interpolation boundary so a path or message containing
``<script>`` is rendered as literal text, not executed.

The output is a **self-contained HTML file**: all CSS and the small
amount of JavaScript live inline. Drop it on a static host (or
attach to a PR comment as ``<details>``) and it renders the same way
without external assets.

The layout intentionally mirrors what ``render_audit_cli`` produces:
header → per-file sections (sorted by path) → cross-artifact →
skipped → summary. The JS layer adds severity filters that toggle
``hidden`` attributes on the diagnostic rows; nothing more.
"""

from __future__ import annotations

import html
from collections.abc import Iterable

from contextos.audit.cross import AuditReport
from contextos.diagnostics import Diagnostic, DiagSeverity


def render_audit_html(report: AuditReport, *, title: str | None = None) -> str:
    """Render the audit report as a single self-contained HTML page."""
    header = _render_header(report, title=title)
    file_sections = _render_file_sections(report)
    cross_section = _render_cross_section(report.cross_artifact)
    skipped_section = _render_skipped_section(report.skipped)
    summary = _render_summary(report)

    body = "\n".join(
        section
        for section in (header, file_sections, cross_section, skipped_section, summary)
        if section
    )

    return _HTML_TEMPLATE.format(
        title=html.escape(title or "ContextOS audit"),
        styles=_STYLES,
        scripts=_SCRIPTS,
        body=body,
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_header(report: AuditReport, *, title: str | None) -> str:
    counts = _count_by_severity(_all_diagnostics(report))
    return (
        '<header class="audit-header">'
        f"<h1>{html.escape(title or 'ContextOS audit')}</h1>"
        f'<p class="repo">{html.escape(str(report.repo_path))}</p>'
        '<div class="filters" role="toolbar">'
        '<button data-filter="all" class="active">All</button>'
        f'<button data-filter="error">Error ({counts["error"]})</button>'
        f'<button data-filter="warning">Warning ({counts["warning"]})</button>'
        f'<button data-filter="info">Info ({counts["info"]})</button>'
        "</div>"
        "</header>"
    )


def _render_file_sections(report: AuditReport) -> str:
    if not report.per_file:
        return ""
    blocks: list[str] = ['<section class="files">', "<h2>Per-file diagnostics</h2>"]
    for path in sorted(report.per_file):
        diags = report.per_file[path]
        blocks.append(_render_file_block(path, diags))
    blocks.append("</section>")
    return "\n".join(blocks)


def _render_file_block(path: str, diags: list[Diagnostic]) -> str:
    if not diags:
        return (
            '<details class="file" open>'
            f"<summary>{html.escape(path)} <span class='ok'>no diagnostics</span></summary>"
            "</details>"
        )
    rows = "".join(_render_diagnostic_row(d) for d in diags)
    return (
        '<details class="file" open>'
        f"<summary>{html.escape(path)} <span class='count'>({len(diags)})</span></summary>"
        f'<table class="diagnostics">{rows}</table>'
        "</details>"
    )


def _render_diagnostic_row(diag: Diagnostic) -> str:
    severity = diag.severity.value
    position = (
        f"{diag.position.line}:{diag.position.column}"
        if diag.position is not None
        else "?"
    )
    code = html.escape(diag.code)
    message = html.escape(diag.message)
    suggestion = (
        f'<div class="suggestion">{html.escape(diag.suggestion)}</div>'
        if diag.suggestion
        else ""
    )
    doc_link = (
        f' <a class="doc-link" href="{html.escape(diag.doc_url)}" target="_blank">doc</a>'
        if diag.doc_url
        else ""
    )
    sev_attr = html.escape(severity)
    return (
        f'<tr class="diagnostic severity-{sev_attr}" data-severity="{sev_attr}">'
        f'<td class="severity">{sev_attr}</td>'
        f'<td class="code">{code}{doc_link}</td>'
        f'<td class="position">{html.escape(position)}</td>'
        f'<td class="message">{message}{suggestion}</td>'
        "</tr>"
    )


def _render_cross_section(diags: list[Diagnostic]) -> str:
    if not diags:
        return ""
    rows = "".join(_render_diagnostic_row(d) for d in diags)
    return (
        '<section class="cross-artifact">'
        f"<h2>Cross-artifact ({len(diags)})</h2>"
        f'<table class="diagnostics">{rows}</table>'
        "</section>"
    )


def _render_skipped_section(entries: list[dict[str, str]]) -> str:
    if not entries:
        return ""
    rows = "".join(
        '<tr><td class="skipped-path">'
        f'{html.escape(str(entry.get("path", "?")))}</td>'
        f'<td>{html.escape(str(entry.get("target", "?")))}</td>'
        f'<td>{html.escape(str(entry.get("reason", "?")))}</td></tr>'
        for entry in entries
    )
    return (
        '<section class="skipped">'
        f"<h2>Skipped ({len(entries)})</h2>"
        '<table class="diagnostics"><thead>'
        "<tr><th>Path</th><th>Target</th><th>Reason</th></tr>"
        f"</thead><tbody>{rows}</tbody></table>"
        "</section>"
    )


def _render_summary(report: AuditReport) -> str:
    return (
        '<footer class="summary">'
        f"<p>Total: {report.total_count()} diagnostic(s).</p>"
        "</footer>"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_diagnostics(report: AuditReport) -> Iterable[Diagnostic]:
    """Iterate every diagnostic across per-file + cross-artifact."""
    for diags in report.per_file.values():
        yield from diags
    yield from report.cross_artifact


def _count_by_severity(diags: Iterable[Diagnostic]) -> dict[str, int]:
    """Return per-severity counts; keys are guaranteed to all exist."""
    counts = {sev.value: 0 for sev in DiagSeverity}
    for d in diags:
        counts[d.severity.value] += 1
    return counts


# ---------------------------------------------------------------------------
# Static assets — inline CSS + JS so the output is one self-contained file.
# ---------------------------------------------------------------------------


_STYLES = """\
:root {
  --error: #c1272d;
  --warning: #d4801f;
  --info: #2a7ab0;
  --bg: #fbfbfd;
  --fg: #1a1a1f;
  --muted: #5d6068;
  --line: #e3e4e8;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg); color: var(--fg);
  margin: 0; padding: 2rem; line-height: 1.45;
}
header.audit-header { border-bottom: 1px solid var(--line); padding-bottom: 1rem; margin-bottom: 1.5rem; }
header.audit-header h1 { margin: 0 0 0.25rem 0; font-size: 1.5rem; }
header.audit-header .repo { color: var(--muted); margin: 0 0 0.75rem 0; font-family: ui-monospace, monospace; font-size: 0.85rem; }
.filters { display: flex; gap: 0.5rem; }
.filters button {
  border: 1px solid var(--line); background: white; padding: 0.25rem 0.75rem;
  border-radius: 999px; cursor: pointer; font-size: 0.85rem;
}
.filters button.active { background: var(--fg); color: white; border-color: var(--fg); }
section { margin-bottom: 1.5rem; }
section h2 { font-size: 1.05rem; margin: 0 0 0.5rem 0; }
details.file { border: 1px solid var(--line); border-radius: 6px; margin-bottom: 0.5rem; background: white; }
details.file summary {
  padding: 0.5rem 0.75rem; cursor: pointer; user-select: none;
  font-family: ui-monospace, monospace; font-size: 0.85rem;
}
details.file summary .count { color: var(--muted); }
details.file summary .ok { color: var(--info); margin-left: 0.5rem; }
table.diagnostics { width: 100%; border-collapse: collapse; }
table.diagnostics tr { border-top: 1px solid var(--line); }
table.diagnostics td, table.diagnostics th { padding: 0.5rem 0.75rem; vertical-align: top; }
table.diagnostics th { text-align: left; font-weight: 600; font-size: 0.85rem; color: var(--muted); }
td.severity { width: 5rem; text-transform: uppercase; font-size: 0.75rem; font-weight: 600; }
tr.severity-error td.severity { color: var(--error); }
tr.severity-warning td.severity { color: var(--warning); }
tr.severity-info td.severity { color: var(--info); }
td.code { width: 7rem; font-family: ui-monospace, monospace; font-size: 0.85rem; }
td.code a.doc-link { color: var(--info); margin-left: 0.25rem; font-size: 0.75rem; text-decoration: none; }
td.code a.doc-link:hover { text-decoration: underline; }
td.position { width: 5rem; color: var(--muted); font-family: ui-monospace, monospace; font-size: 0.85rem; }
td.message { color: var(--fg); }
td.message .suggestion {
  color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; padding-left: 0.5rem;
  border-left: 2px solid var(--line);
}
footer.summary { color: var(--muted); font-size: 0.85rem; padding-top: 1rem; border-top: 1px solid var(--line); }
"""


_SCRIPTS = """\
document.querySelectorAll('.filters button').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.filter;
    document.querySelectorAll('.filters button').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('tr.diagnostic').forEach(row => {
      row.hidden = target !== 'all' && row.dataset.severity !== target;
    });
  });
});
"""


_HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{styles}
</style>
</head>
<body>
{body}
<script>
{scripts}
</script>
</body>
</html>
"""


__all__ = ["render_audit_html"]
