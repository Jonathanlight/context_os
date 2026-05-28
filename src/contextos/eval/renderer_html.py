"""HTML eval report — Phase 8.4.

Hand-rolled HTML renderer for :class:`EvalRunResult`. Same patterns
as :mod:`contextos.audit.renderer_html`: ``html.escape`` at every
interpolation, no templating engine, all CSS + JS inlined so the
file is one self-contained artifact.

The layout puts the **pass rate** front and center (the metric
operators stare at most) plus a token total (the metric finance
stares at most). Cases render as a filterable table with PASS /
FAIL chips; failing cases expand inline to show expected / actual /
error.
"""

from __future__ import annotations

import html

from contextos.eval.results import EvalRunResult


def render_eval_html(result: EvalRunResult, *, title: str | None = None) -> str:
    """Render the run as a single self-contained HTML page."""
    header = _render_header(result, title=title)
    rows = _render_cases(result)
    summary = _render_summary(result)

    body = "\n".join(filter(None, (header, rows, summary)))
    return _HTML_TEMPLATE.format(
        title=html.escape(title or f"ContextOS eval — {result.suite_project}"),
        styles=_STYLES,
        scripts=_SCRIPTS,
        body=body,
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_header(result: EvalRunResult, *, title: str | None) -> str:
    total = len(result.case_results)
    pct = round(result.pass_rate * 100)
    page_title = title or f"ContextOS eval — {result.suite_project}"
    return (
        '<header class="eval-header">'
        f"<h1>{html.escape(page_title)}</h1>"
        '<div class="meta">'
        f'<span class="badge target">{html.escape(result.target)}</span>'
        f'<span class="badge tokens">{result.total_tokens} tokens</span>'
        "</div>"
        '<div class="rate-block">'
        f'<div class="rate-num">{pct}%</div>'
        f'<div class="rate-bar"><div class="rate-bar-fill" style="width:{pct}%"></div></div>'
        f'<div class="rate-label">{result.pass_count}/{total} passing</div>'
        "</div>"
        '<div class="filters" role="toolbar">'
        '<button data-filter="all" class="active">All</button>'
        f'<button data-filter="pass">Pass ({result.pass_count})</button>'
        f'<button data-filter="fail">Fail ({result.fail_count})</button>'
        "</div>"
        "</header>"
    )


def _render_cases(result: EvalRunResult) -> str:
    if not result.case_results:
        return '<section class="cases empty"><p>No cases were run.</p></section>'
    rows = "".join(_render_case_row(case) for case in result.case_results)
    return (
        '<section class="cases">'
        '<table class="case-table">'
        "<thead><tr>"
        '<th class="col-status">Status</th>'
        '<th class="col-name">Case</th>'
        '<th class="col-expected">Expected</th>'
        '<th class="col-actual">Actual</th>'
        '<th class="col-tokens">Tokens</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</section>"
    )


def _render_case_row(case: object) -> str:
    # The eval module's EvalCaseResult is a Pydantic model; we duck-type
    # the attributes here to keep the renderer importable without
    # circularizing through results.py.
    passed = getattr(case, "passed", False)
    case_name = str(getattr(case, "case_name", ""))
    expected = str(getattr(case, "expected", ""))
    actual = getattr(case, "actual", None)
    tokens_used = getattr(case, "tokens_used", None)
    error = getattr(case, "error", None)

    status_class = "pass" if passed else "fail"
    status_label = "PASS" if passed else "FAIL"
    actual_text = html.escape(str(actual)) if actual is not None else "<em>(none)</em>"
    tokens_cell = str(tokens_used) if tokens_used is not None else "&ndash;"
    error_block = (
        f'<div class="error-note">{html.escape(str(error))}</div>'
        if error
        else ""
    )

    return (
        f'<tr class="case {status_class}" data-status="{status_class}">'
        f'<td class="col-status"><span class="chip chip-{status_class}">{status_label}</span></td>'
        f'<td class="col-name">{html.escape(case_name)}{error_block}</td>'
        f'<td class="col-expected">{html.escape(expected)}</td>'
        f'<td class="col-actual">{actual_text}</td>'
        f'<td class="col-tokens">{tokens_cell}</td>'
        "</tr>"
    )


def _render_summary(result: EvalRunResult) -> str:
    return (
        '<footer class="eval-summary">'
        f"<p>Suite: <code>{html.escape(result.suite_project)}</code> &middot; "
        f"target <code>{html.escape(result.target)}</code> &middot; "
        f"{len(result.case_results)} case(s), "
        f"{result.total_tokens} tokens total.</p>"
        "</footer>"
    )


# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------

_STYLES = """\
:root {
  --pass: #2f8a3c;
  --fail: #c1272d;
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
header.eval-header { border-bottom: 1px solid var(--line); padding-bottom: 1.25rem; margin-bottom: 1.5rem; }
header.eval-header h1 { margin: 0 0 0.5rem 0; font-size: 1.5rem; }
.meta { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.badge { background: white; border: 1px solid var(--line); padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8rem; color: var(--muted); }
.badge.target { font-family: ui-monospace, monospace; }
.rate-block { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
.rate-num { font-size: 2.5rem; font-weight: 700; min-width: 5rem; }
.rate-bar { flex: 1; height: 0.6rem; background: var(--line); border-radius: 999px; overflow: hidden; }
.rate-bar-fill { height: 100%; background: var(--pass); transition: width 0.3s; }
.rate-label { color: var(--muted); font-size: 0.9rem; min-width: 8rem; text-align: right; }
.filters { display: flex; gap: 0.5rem; }
.filters button { border: 1px solid var(--line); background: white; padding: 0.25rem 0.75rem; border-radius: 999px; cursor: pointer; font-size: 0.85rem; }
.filters button.active { background: var(--fg); color: white; border-color: var(--fg); }
table.case-table { width: 100%; border-collapse: collapse; background: white; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
table.case-table th, table.case-table td { padding: 0.6rem 0.75rem; border-top: 1px solid var(--line); text-align: left; vertical-align: top; }
table.case-table thead th { border-top: 0; background: #f5f5f7; font-weight: 600; font-size: 0.85rem; color: var(--muted); }
td.col-status, th.col-status { width: 5rem; }
td.col-tokens, th.col-tokens { width: 5rem; text-align: right; font-family: ui-monospace, monospace; font-size: 0.85rem; color: var(--muted); }
td.col-name { font-family: ui-monospace, monospace; font-size: 0.9rem; }
td.col-expected, td.col-actual { font-family: ui-monospace, monospace; font-size: 0.85rem; word-break: break-word; }
.chip { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
.chip-pass { background: rgba(47, 138, 60, 0.12); color: var(--pass); }
.chip-fail { background: rgba(193, 39, 45, 0.12); color: var(--fail); }
tr.case.fail td.col-actual em { color: var(--muted); }
.error-note { color: var(--fail); font-size: 0.8rem; margin-top: 0.3rem; padding-left: 0.5rem; border-left: 2px solid var(--fail); font-family: ui-monospace, monospace; }
section.cases.empty { text-align: center; padding: 3rem; color: var(--muted); }
footer.eval-summary { color: var(--muted); font-size: 0.85rem; padding-top: 1rem; border-top: 1px solid var(--line); margin-top: 1.5rem; }
footer.eval-summary code { background: white; padding: 0.05rem 0.3rem; border: 1px solid var(--line); border-radius: 4px; font-family: ui-monospace, monospace; }
"""


_SCRIPTS = """\
document.querySelectorAll('.filters button').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.filter;
    document.querySelectorAll('.filters button').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('tr.case').forEach(row => {
      row.hidden = target !== 'all' && row.dataset.status !== target;
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


__all__ = ["render_eval_html"]
