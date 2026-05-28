"""Tests for the agent-family DocumentDiff and diff_documents."""

from __future__ import annotations

from contextos.ast.agent import (
    AgentDocument,
    Identity,
    Rule,
    Stack,
    Style,
    Tools,
)
from contextos.ast.common import Severity
from contextos.ast.document import Document
from contextos.diff import diff_documents


def _doc(
    *,
    project: str = "P",
    agent: AgentDocument | None = None,
) -> Document:
    return Document(
        project=project,
        agent=agent if agent is not None else AgentDocument(),
    )


def _rule(
    rid: str,
    title: str = "t",
    severity: Severity = Severity.MUST,
    rationale: str | None = None,
    tags: list[str] | None = None,
    applies_to: list[str] | None = None,
) -> Rule:
    return Rule(
        id=rid,
        title=title,
        severity=severity,
        rationale=rationale,
        tags=tags or [],
        applies_to=applies_to or [],
    )


class TestDiffEmpty:
    def test_identical_docs_yield_empty_diff(self) -> None:
        doc = _doc(agent=AgentDocument(rules=[_rule("X-001")]))
        assert diff_documents(doc, doc).is_empty()

    def test_empty_diff_json_serialization(self) -> None:
        doc = _doc()
        d = diff_documents(doc, doc)
        # Pydantic round-trip should hold for empty diff.
        restored = d.model_validate_json(d.model_dump_json())
        assert restored == d


class TestProjectChange:
    def test_project_change_detected(self) -> None:
        a = _doc(project="Old")
        b = _doc(project="New")
        diff = diff_documents(a, b)
        assert diff.project_changed == ("Old", "New")

    def test_project_unchanged_is_none(self) -> None:
        diff = diff_documents(_doc(project="Same"), _doc(project="Same"))
        assert diff.project_changed is None


class TestIdentity:
    def test_role_added(self) -> None:
        diff = diff_documents(
            _doc(),
            _doc(agent=AgentDocument(identity=Identity(role="r"))),
        )
        assert diff.identity_role_changed == (None, "r")

    def test_role_removed(self) -> None:
        diff = diff_documents(
            _doc(agent=AgentDocument(identity=Identity(role="r"))),
            _doc(),
        )
        assert diff.identity_role_changed == ("r", None)

    def test_role_changed(self) -> None:
        diff = diff_documents(
            _doc(agent=AgentDocument(identity=Identity(role="senior"))),
            _doc(agent=AgentDocument(identity=Identity(role="principal"))),
        )
        assert diff.identity_role_changed == ("senior", "principal")

    def test_role_same_yields_none(self) -> None:
        agent = AgentDocument(identity=Identity(role="r"))
        diff = diff_documents(_doc(agent=agent), _doc(agent=agent))
        assert diff.identity_role_changed is None


class TestStackDiff:
    def test_required_added(self) -> None:
        diff = diff_documents(
            _doc(agent=AgentDocument(stack=Stack(required=["python"]))),
            _doc(agent=AgentDocument(stack=Stack(required=["python", "fastapi"]))),
        )
        assert diff.stack_diff.required_added == ["fastapi"]
        assert diff.stack_diff.required_removed == []

    def test_required_removed(self) -> None:
        diff = diff_documents(
            _doc(agent=AgentDocument(stack=Stack(required=["python", "django"]))),
            _doc(agent=AgentDocument(stack=Stack(required=["python"]))),
        )
        assert diff.stack_diff.required_removed == ["django"]

    def test_all_buckets_change_independently(self) -> None:
        a = AgentDocument(stack=Stack(required=["python"], forbidden=["jquery"]))
        b = AgentDocument(stack=Stack(required=["python", "fastapi"], preferred=["uvloop"]))
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.stack_diff.required_added == ["fastapi"]
        assert diff.stack_diff.forbidden_removed == ["jquery"]
        assert diff.stack_diff.preferred_added == ["uvloop"]

    def test_no_stack_change_is_empty(self) -> None:
        agent = AgentDocument(stack=Stack(required=["python"]))
        diff = diff_documents(_doc(agent=agent), _doc(agent=agent))
        assert diff.stack_diff.is_empty()


class TestRulesAddedRemoved:
    def test_rule_added(self) -> None:
        a = AgentDocument(rules=[_rule("A-001")])
        b = AgentDocument(rules=[_rule("A-001"), _rule("B-002", "new")])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert [r.id for r in diff.rules_added] == ["B-002"]
        assert diff.rules_removed == []

    def test_rule_removed(self) -> None:
        a = AgentDocument(rules=[_rule("A-001"), _rule("B-002")])
        b = AgentDocument(rules=[_rule("A-001")])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert [r.id for r in diff.rules_removed] == ["B-002"]

    def test_rule_modified_title(self) -> None:
        a = AgentDocument(rules=[_rule("A-001", title="old")])
        b = AgentDocument(rules=[_rule("A-001", title="new")])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert len(diff.rules_modified) == 1
        assert diff.rules_modified[0].title_changed == ("old", "new")

    def test_rule_modified_severity(self) -> None:
        a = AgentDocument(rules=[_rule("A-001", severity=Severity.SHOULD)])
        b = AgentDocument(rules=[_rule("A-001", severity=Severity.MUST)])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.rules_modified[0].severity_changed == (
            Severity.SHOULD,
            Severity.MUST,
        )

    def test_rule_modified_tags(self) -> None:
        a = AgentDocument(rules=[_rule("A-001", tags=["security"])])
        b = AgentDocument(rules=[_rule("A-001", tags=["security", "owasp"])])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.rules_modified[0].tags_added == ["owasp"]
        assert diff.rules_modified[0].tags_removed == []

    def test_unchanged_rule_does_not_appear_in_modified(self) -> None:
        a = AgentDocument(rules=[_rule("A-001"), _rule("B-002")])
        b = AgentDocument(rules=[_rule("A-001"), _rule("B-002", severity=Severity.MAY)])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        # A-001 is unchanged; only B-002 is in modified.
        modified_ids = [r.rule_id for r in diff.rules_modified]
        assert modified_ids == ["B-002"]


class TestStyleAndForbidden:
    def test_style_added_removed(self) -> None:
        a = AgentDocument(style=Style(conventions=["2 spaces"]))
        b = AgentDocument(style=Style(conventions=["4 spaces"]))
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.style_added == ["4 spaces"]
        assert diff.style_removed == ["2 spaces"]

    def test_forbidden_added_removed(self) -> None:
        a = AgentDocument(forbidden_patterns=["jQuery", "raw SQL"])
        b = AgentDocument(forbidden_patterns=["raw SQL", "wildcard imports"])
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.forbidden_added == ["wildcard imports"]
        assert diff.forbidden_removed == ["jQuery"]


class TestToolsDiff:
    def test_required_added_removed(self) -> None:
        a = AgentDocument(tools=Tools(required=["ruff"], forbidden=["black"]))
        b = AgentDocument(tools=Tools(required=["ruff", "mypy"], forbidden=[]))
        diff = diff_documents(_doc(agent=a), _doc(agent=b))
        assert diff.tools_diff.required_added == ["mypy"]
        assert diff.tools_diff.forbidden_removed == ["black"]


class TestIsEmpty:
    def test_only_project_changed_is_not_empty(self) -> None:
        diff = diff_documents(_doc(project="a"), _doc(project="b"))
        assert not diff.is_empty()

    def test_only_rule_modified_is_not_empty(self) -> None:
        a = AgentDocument(rules=[_rule("A-001", title="old")])
        b = AgentDocument(rules=[_rule("A-001", title="new")])
        assert not diff_documents(_doc(agent=a), _doc(agent=b)).is_empty()
