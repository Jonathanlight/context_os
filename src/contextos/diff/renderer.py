"""Renderers for :class:`DocumentDiff` — CLI text and JSON shapes."""

from __future__ import annotations

import json
from typing import Any

from contextos.diff.agent import DocumentDiff, RuleDiff, StackDiff, ToolsDiff


def render_diff_cli(diff: DocumentDiff) -> str:
    """Render a :class:`DocumentDiff` as human-readable text.

    Empty diffs render as a single ``no changes`` line. Otherwise each
    populated section gets a header followed by ``+``/``-``/``~`` lines.
    """
    if diff.is_empty():
        return "no changes\n"

    parts: list[str] = []

    if diff.project_changed is not None:
        proj_old, proj_new = diff.project_changed
        parts.append(f"project: {proj_old!r} -> {proj_new!r}")

    if diff.identity_role_changed is not None:
        role_old, role_new = diff.identity_role_changed
        parts.extend(["", "identity:", f"  ~ role: {role_old!r} -> {role_new!r}"])

    parts.extend(_render_stack(diff.stack_diff))
    parts.extend(_render_rules(diff))
    parts.extend(_render_string_list("style", diff.style_added, diff.style_removed))
    parts.extend(
        _render_string_list("forbidden_patterns", diff.forbidden_added, diff.forbidden_removed)
    )
    parts.extend(_render_tools(diff.tools_diff))

    return "\n".join(parts).rstrip() + "\n"


def render_diff_json(diff: DocumentDiff, *, indent: int | None = None) -> str:
    """Render the diff as JSON. Pydantic handles tuple → 2-element list."""
    payload = diff.model_dump(mode="json")
    return json.dumps(payload, indent=indent, sort_keys=True)


def _render_stack(stack: StackDiff) -> list[str]:
    if stack.is_empty():
        return []
    parts = ["", "stack:"]
    parts.extend(_render_bucket("required", stack.required_added, stack.required_removed))
    parts.extend(_render_bucket("forbidden", stack.forbidden_added, stack.forbidden_removed))
    parts.extend(_render_bucket("preferred", stack.preferred_added, stack.preferred_removed))
    return parts


def _render_tools(tools: ToolsDiff) -> list[str]:
    if tools.is_empty():
        return []
    parts = ["", "tools:"]
    parts.extend(_render_bucket("required", tools.required_added, tools.required_removed))
    parts.extend(_render_bucket("forbidden", tools.forbidden_added, tools.forbidden_removed))
    return parts


def _render_bucket(label: str, added: list[str], removed: list[str]) -> list[str]:
    if not added and not removed:
        return []
    parts: list[str] = [f"  {label}:"]
    parts.extend(f"    + {item}" for item in added)
    parts.extend(f"    - {item}" for item in removed)
    return parts


def _render_string_list(section: str, added: list[str], removed: list[str]) -> list[str]:
    if not added and not removed:
        return []
    parts = ["", f"{section}:"]
    parts.extend(f"  + {item}" for item in added)
    parts.extend(f"  - {item}" for item in removed)
    return parts


def _render_rules(diff: DocumentDiff) -> list[str]:
    if not (diff.rules_added or diff.rules_removed or diff.rules_modified):
        return []
    parts = ["", "rules:"]
    for rule in diff.rules_added:
        parts.append(f"  + {rule.id}: {rule.title}")
    for rule in diff.rules_removed:
        parts.append(f"  - {rule.id}: {rule.title}")
    for rule_diff in diff.rules_modified:
        parts.append(f"  ~ {rule_diff.rule_id}:")
        parts.extend(_render_rule_changes(rule_diff))
    return parts


def _render_rule_changes(rule_diff: RuleDiff) -> list[str]:
    parts: list[str] = []
    if rule_diff.title_changed is not None:
        old, new = rule_diff.title_changed
        parts.append(f"      title: {old!r} -> {new!r}")
    if rule_diff.severity_changed is not None:
        old_sev, new_sev = rule_diff.severity_changed
        parts.append(f"      severity: {old_sev.value} -> {new_sev.value}")
    if rule_diff.rationale_changed is not None:
        old_r, new_r = rule_diff.rationale_changed
        parts.append(f"      rationale: {old_r!r} -> {new_r!r}")
    parts.extend(
        _inline_added_removed(
            "applies_to", rule_diff.applies_to_added, rule_diff.applies_to_removed
        )
    )
    parts.extend(_inline_added_removed("tags", rule_diff.tags_added, rule_diff.tags_removed))
    return parts


def _inline_added_removed(label: str, added: list[str], removed: list[str]) -> list[str]:
    if not added and not removed:
        return []
    parts: list[str] = []
    if added:
        parts.append(f"      {label} +: {sorted(added)}")
    if removed:
        parts.append(f"      {label} -: {sorted(removed)}")
    return parts


_RENDER_HELPERS: tuple[Any, ...] = (StackDiff, ToolsDiff)  # keep type imports visible
