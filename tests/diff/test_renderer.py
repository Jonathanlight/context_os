"""Tests for diff renderers (CLI text + JSON)."""

from __future__ import annotations

import json

from contextos.ast.agent import (
    AgentDocument,
    Identity,
    Rule,
    Stack,
    Style,
)
from contextos.ast.common import Severity
from contextos.ast.document import Document
from contextos.diff import diff_documents, render_diff_cli, render_diff_json


def _doc(agent: AgentDocument | None = None, project: str = "P") -> Document:
    return Document(
        project=project,
        agent=agent if agent is not None else AgentDocument(),
    )


class TestCliRendering:
    def test_empty_diff_shows_no_changes(self) -> None:
        doc = _doc()
        out = render_diff_cli(diff_documents(doc, doc))
        assert out == "no changes\n"

    def test_project_change_rendered(self) -> None:
        out = render_diff_cli(diff_documents(_doc(project="a"), _doc(project="b")))
        assert "project: 'a' -> 'b'" in out

    def test_stack_required_added(self) -> None:
        a = AgentDocument(stack=Stack(required=["python"]))
        b = AgentDocument(stack=Stack(required=["python", "fastapi"]))
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "stack:" in out
        assert "+ fastapi" in out

    def test_rule_added(self) -> None:
        a = AgentDocument()
        b = AgentDocument(rules=[Rule(id="A-001", title="t", severity=Severity.MUST)])
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "rules:" in out
        assert "+ A-001: t" in out

    def test_rule_removed(self) -> None:
        a = AgentDocument(rules=[Rule(id="A-001", title="t", severity=Severity.MUST)])
        b = AgentDocument()
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "- A-001: t" in out

    def test_rule_severity_change(self) -> None:
        a = AgentDocument(rules=[Rule(id="A-001", title="t", severity=Severity.SHOULD)])
        b = AgentDocument(rules=[Rule(id="A-001", title="t", severity=Severity.MUST)])
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "~ A-001:" in out
        assert "severity: should -> must" in out

    def test_identity_change(self) -> None:
        a = AgentDocument(identity=Identity(role="senior"))
        b = AgentDocument(identity=Identity(role="principal"))
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "identity:" in out
        assert "role: 'senior' -> 'principal'" in out

    def test_style_changes(self) -> None:
        a = AgentDocument(style=Style(conventions=["2 spaces"]))
        b = AgentDocument(style=Style(conventions=["4 spaces"]))
        out = render_diff_cli(diff_documents(_doc(agent=a), _doc(agent=b)))
        assert "style:" in out
        assert "+ 4 spaces" in out
        assert "- 2 spaces" in out

    def test_trailing_newline(self) -> None:
        out = render_diff_cli(diff_documents(_doc(project="a"), _doc(project="b")))
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


class TestJsonRendering:
    def test_empty_diff_json_shape(self) -> None:
        doc = _doc()
        payload = json.loads(render_diff_json(diff_documents(doc, doc)))
        assert payload["project_changed"] is None
        assert payload["rules_added"] == []
        assert payload["rules_removed"] == []
        assert payload["rules_modified"] == []

    def test_project_change_json_uses_two_element_array(self) -> None:
        payload = json.loads(render_diff_json(diff_documents(_doc(project="a"), _doc(project="b"))))
        # Pydantic serializes tuple as JSON array.
        assert payload["project_changed"] == ["a", "b"]

    def test_indent(self) -> None:
        out = render_diff_json(
            diff_documents(_doc(project="a"), _doc(project="b")),
            indent=2,
        )
        assert "\n" in out
        assert '"project_changed"' in out
