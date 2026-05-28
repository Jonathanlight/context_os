"""Diff data model and the :func:`diff_documents` function.

The diff is structured (Pydantic models). Each section carries its own
sub-diff so renderers can format them independently. Rules diff by
``Rule.id`` — same id = same rule (modified); ids only in one side =
added or removed.

The diff is **semantic**, not textual. Two Documents that produce
byte-identical Markdown will diff cleanly to an empty DocumentDiff;
two that differ only in formatting (whitespace, comment ordering) will
also produce an empty diff because both parse to the same AST.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contextos.ast.agent import AgentDocument, Identity, Rule, Stack, Tools
from contextos.ast.common import Severity
from contextos.ast.document import Document


class StackDiff(BaseModel):
    """Per-bucket added / removed lists for :class:`Stack`."""

    model_config = ConfigDict(extra="forbid")

    required_added: list[str] = []
    required_removed: list[str] = []
    forbidden_added: list[str] = []
    forbidden_removed: list[str] = []
    preferred_added: list[str] = []
    preferred_removed: list[str] = []

    def is_empty(self) -> bool:
        return not any(
            (
                self.required_added,
                self.required_removed,
                self.forbidden_added,
                self.forbidden_removed,
                self.preferred_added,
                self.preferred_removed,
            )
        )


class ToolsDiff(BaseModel):
    """Per-bucket added / removed lists for :class:`Tools`."""

    model_config = ConfigDict(extra="forbid")

    required_added: list[str] = []
    required_removed: list[str] = []
    forbidden_added: list[str] = []
    forbidden_removed: list[str] = []

    def is_empty(self) -> bool:
        return not any(
            (
                self.required_added,
                self.required_removed,
                self.forbidden_added,
                self.forbidden_removed,
            )
        )


class RuleDiff(BaseModel):
    """Field-level diff of a single rule (matched by ``rule_id``)."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title_changed: tuple[str, str] | None = None
    severity_changed: tuple[Severity, Severity] | None = None
    rationale_changed: tuple[str | None, str | None] | None = None
    applies_to_added: list[str] = []
    applies_to_removed: list[str] = []
    tags_added: list[str] = []
    tags_removed: list[str] = []

    def is_empty(self) -> bool:
        return not any(
            (
                self.title_changed,
                self.severity_changed,
                self.rationale_changed,
                self.applies_to_added,
                self.applies_to_removed,
                self.tags_added,
                self.tags_removed,
            )
        )


class DocumentDiff(BaseModel):
    """Top-level diff between two :class:`Document` instances.

    Only fields that changed are populated; an unchanged Document diff
    has :meth:`is_empty` true.
    """

    model_config = ConfigDict(extra="forbid")

    project_changed: tuple[str, str] | None = None
    identity_role_changed: tuple[str | None, str | None] | None = None
    stack_diff: StackDiff = StackDiff()
    rules_added: list[Rule] = []
    rules_removed: list[Rule] = []
    rules_modified: list[RuleDiff] = []
    style_added: list[str] = []
    style_removed: list[str] = []
    forbidden_added: list[str] = []
    forbidden_removed: list[str] = []
    tools_diff: ToolsDiff = ToolsDiff()

    def is_empty(self) -> bool:
        return not any(
            (
                self.project_changed,
                self.identity_role_changed,
                not self.stack_diff.is_empty(),
                self.rules_added,
                self.rules_removed,
                self.rules_modified,
                self.style_added,
                self.style_removed,
                self.forbidden_added,
                self.forbidden_removed,
                not self.tools_diff.is_empty(),
            )
        )


def diff_documents(a: Document, b: Document) -> DocumentDiff:
    """Compare two Documents at the AST level.

    Returns a :class:`DocumentDiff` with only changed fields populated.
    Both Documents are expected to be ``type=agent``; behaviour on other
    types is undefined until Phase 5 (skill) and Phase 6 (rag) land.
    """
    project_changed = (a.project, b.project) if a.project != b.project else None

    agent_a = a.agent or AgentDocument()
    agent_b = b.agent or AgentDocument()

    return DocumentDiff(
        project_changed=project_changed,
        identity_role_changed=_diff_identity(agent_a.identity, agent_b.identity),
        stack_diff=_diff_stack(agent_a.stack, agent_b.stack),
        **_diff_rules(agent_a.rules, agent_b.rules),
        style_added=_added(_style(agent_a), _style(agent_b)),
        style_removed=_removed(_style(agent_a), _style(agent_b)),
        forbidden_added=_added(agent_a.forbidden_patterns, agent_b.forbidden_patterns),
        forbidden_removed=_removed(agent_a.forbidden_patterns, agent_b.forbidden_patterns),
        tools_diff=_diff_tools(agent_a.tools, agent_b.tools),
    )


def _style(agent: AgentDocument) -> list[str]:
    return list(agent.style.conventions) if agent.style is not None else []


def _diff_identity(a: Identity | None, b: Identity | None) -> tuple[str | None, str | None] | None:
    role_a = a.role if a is not None else None
    role_b = b.role if b is not None else None
    if role_a == role_b:
        return None
    return (role_a, role_b)


def _diff_stack(a: Stack | None, b: Stack | None) -> StackDiff:
    stack_a = a or Stack()
    stack_b = b or Stack()
    return StackDiff(
        required_added=_added(stack_a.required, stack_b.required),
        required_removed=_removed(stack_a.required, stack_b.required),
        forbidden_added=_added(stack_a.forbidden, stack_b.forbidden),
        forbidden_removed=_removed(stack_a.forbidden, stack_b.forbidden),
        preferred_added=_added(stack_a.preferred, stack_b.preferred),
        preferred_removed=_removed(stack_a.preferred, stack_b.preferred),
    )


def _diff_tools(a: Tools | None, b: Tools | None) -> ToolsDiff:
    tools_a = a or Tools()
    tools_b = b or Tools()
    return ToolsDiff(
        required_added=_added(tools_a.required, tools_b.required),
        required_removed=_removed(tools_a.required, tools_b.required),
        forbidden_added=_added(tools_a.forbidden, tools_b.forbidden),
        forbidden_removed=_removed(tools_a.forbidden, tools_b.forbidden),
    )


def _diff_rules(a: list[Rule], b: list[Rule]) -> dict[str, object]:
    by_id_a = {rule.id: rule for rule in a}
    by_id_b = {rule.id: rule for rule in b}

    added_ids = sorted(set(by_id_b) - set(by_id_a))
    removed_ids = sorted(set(by_id_a) - set(by_id_b))
    common_ids = sorted(set(by_id_a) & set(by_id_b))

    rules_modified: list[RuleDiff] = []
    for rule_id in common_ids:
        rule_diff = _diff_rule(by_id_a[rule_id], by_id_b[rule_id])
        if not rule_diff.is_empty():
            rules_modified.append(rule_diff)

    return {
        "rules_added": [by_id_b[rid] for rid in added_ids],
        "rules_removed": [by_id_a[rid] for rid in removed_ids],
        "rules_modified": rules_modified,
    }


def _diff_rule(a: Rule, b: Rule) -> RuleDiff:
    return RuleDiff(
        rule_id=a.id,
        title_changed=(a.title, b.title) if a.title != b.title else None,
        severity_changed=((a.severity, b.severity) if a.severity != b.severity else None),
        rationale_changed=((a.rationale, b.rationale) if a.rationale != b.rationale else None),
        applies_to_added=_added(a.applies_to, b.applies_to),
        applies_to_removed=_removed(a.applies_to, b.applies_to),
        tags_added=_added(a.tags, b.tags),
        tags_removed=_removed(a.tags, b.tags),
    )


def _added(a: list[str], b: list[str]) -> list[str]:
    """Items present in ``b`` but not in ``a``, in stable b-order."""
    seen = set(a)
    return [item for item in b if item not in seen]


def _removed(a: list[str], b: list[str]) -> list[str]:
    """Items present in ``a`` but not in ``b``, in stable a-order."""
    seen = set(b)
    return [item for item in a if item not in seen]
