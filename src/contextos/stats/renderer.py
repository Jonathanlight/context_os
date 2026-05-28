"""Renderers for :class:`CorpusStats` — CLI text + JSON."""

from __future__ import annotations

import json

from contextos.stats.aggregator import CorpusStats


def render_stats_cli(stats: CorpusStats) -> str:
    """Render the corpus stats as a human-readable summary table."""
    if stats.is_empty():
        return "no files audited\n"

    parts: list[str] = [f"corpus stats: {stats.repo_path}"]
    parts.append("")
    parts.append(f"files audited:  {stats.files_audited}")
    parts.append(f"files skipped:  {stats.files_skipped}")
    parts.append(f"diagnostics:    {stats.total_diagnostics}")

    if stats.total_diagnostics:
        parts.append("")
        parts.append("by severity:")
        for sev, count in stats.diagnostics_by_severity.items():
            parts.append(f"  {sev:<7} {count}")

    if stats.top_codes:
        parts.append("")
        parts.append("top codes:")
        for code, count in stats.top_codes:
            parts.append(f"  {code:<6} {count}")

    if stats.target_coverage:
        parts.append("")
        parts.append("target coverage:")
        for target, count in sorted(stats.target_coverage.items()):
            parts.append(f"  {target:<14} {count}")

    return "\n".join(parts).rstrip() + "\n"


def render_stats_json(stats: CorpusStats, *, indent: int | None = None) -> str:
    """Render the corpus stats as JSON."""
    payload = stats.model_dump(mode="json")
    return json.dumps(payload, indent=indent, sort_keys=True)
