"""Tests for the context-family AST submodels."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.ast.agent import (
    AgentDocument,
    Identity,
    Rule,
    Stack,
    Style,
    Tools,
)
from contextos.ast.common import Position, ProseBlock, Severity


class TestIdentity:
    def test_minimal_identity(self) -> None:
        i = Identity(role="senior engineer")
        assert i.role == "senior engineer"
        assert i.context is None
        assert i.author is None

    def test_full_identity(self) -> None:
        i = Identity(role="r", context="c", author="a")
        assert i.context == "c"
        assert i.author == "a"

    def test_role_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            Identity(role="")

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Identity(role="x", title="y")  # type: ignore[call-arg]


class TestStack:
    def test_defaults_to_empty_lists(self) -> None:
        s = Stack()
        assert s.required == []
        assert s.forbidden == []
        assert s.preferred == []

    def test_populated_lists(self) -> None:
        s = Stack(required=["python>=3.12"], forbidden=["django"])
        assert s.required == ["python>=3.12"]
        assert s.forbidden == ["django"]


class TestStyle:
    def test_default_empty(self) -> None:
        assert Style().conventions == []

    def test_with_conventions(self) -> None:
        s = Style(conventions=["4 spaces", "snake_case"])
        assert len(s.conventions) == 2


class TestTools:
    def test_default_empty(self) -> None:
        t = Tools()
        assert t.required == []
        assert t.forbidden == []

    def test_with_tools(self) -> None:
        t = Tools(required=["ruff", "mypy"], forbidden=["black"])
        assert "ruff" in t.required


class TestRule:
    def test_minimal_valid_rule(self) -> None:
        r = Rule(id="TDD-001", title="Tests before code", severity=Severity.MUST)
        assert r.id == "TDD-001"
        assert r.severity == Severity.MUST
        assert r.applies_to == []
        assert r.tags == []
        assert r.rationale is None

    def test_full_rule(self) -> None:
        r = Rule(
            id="SEC-042",
            title="Sanitize user input",
            severity=Severity.MUST,
            applies_to=["api"],
            rationale="prevent injection",
            detail="run validators",
            example_good="bleach.clean(x)",
            example_bad="raw concatenation",
            tags=["security"],
            links=["https://owasp.org"],
            position=Position(file="rules.ctx", line=12),
        )
        assert r.position is not None
        assert r.position.line == 12

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Rule(
                id="X-001",
                title="t",
                severity=Severity.MAY,
                priority=5,  # type: ignore[call-arg]
            )

    @pytest.mark.parametrize(
        "valid_id",
        ["TDD-001", "SEC-042", "LINT-12345", "A-100", "VERYLONG-999"],
    )
    def test_id_pattern_accepts_valid(self, valid_id: str) -> None:
        r = Rule(id=valid_id, title="t", severity=Severity.MAY)
        assert r.id == valid_id

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "tdd-001",  # lowercase
            "T-01",  # < 3 digits
            "001-TDD",  # digits-first
            "TDD_001",  # underscore not hyphen
            "TDD001",  # missing hyphen
            "",  # empty
            "TDD-",  # no digits
            "-001",  # no prefix
        ],
    )
    def test_id_pattern_rejects_invalid(self, invalid_id: str) -> None:
        with pytest.raises(ValidationError):
            Rule(id=invalid_id, title="t", severity=Severity.MAY)

    def test_severity_must_be_known(self) -> None:
        with pytest.raises(ValidationError):
            Rule(id="X-001", title="t", severity="maybe")

    def test_title_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            Rule(id="X-001", title="", severity=Severity.MAY)

    def test_round_trips_via_json(self) -> None:
        original = Rule(
            id="TDD-001",
            title="Tests first",
            severity=Severity.MUST,
            tags=["testing", "tdd"],
        )
        restored = Rule.model_validate_json(original.model_dump_json())
        assert restored == original


class TestAgentDocument:
    def test_empty_document(self) -> None:
        d = AgentDocument()
        assert d.rules == []
        assert d.identity is None
        assert d.prose == []

    def test_full_document(self) -> None:
        d = AgentDocument(
            identity=Identity(role="r"),
            stack=Stack(required=["python"]),
            style=Style(conventions=["pep8"]),
            tools=Tools(required=["ruff"]),
            rules=[Rule(id="X-001", title="t", severity=Severity.MAY)],
            forbidden_patterns=["raw SQL strings", "wildcard imports"],
            prose=[ProseBlock(content="hi")],
        )
        assert d.identity is not None
        assert d.identity.role == "r"
        assert len(d.rules) == 1
        assert "wildcard imports" in d.forbidden_patterns

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            AgentDocument(extras={})  # type: ignore[call-arg]

    def test_round_trips_via_json(self) -> None:
        original = AgentDocument(
            identity=Identity(role="r"),
            rules=[Rule(id="X-001", title="t", severity=Severity.SHOULD)],
        )
        restored = AgentDocument.model_validate_json(original.model_dump_json())
        assert restored == original
