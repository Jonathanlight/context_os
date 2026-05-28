"""Unit tests for :func:`build_starter_document`."""

from __future__ import annotations

from contextos.ast.common import Severity
from contextos.parsers import dump_ctx_string, parse_ctx_string
from contextos.scaffold import build_starter_document


def test_build_minimal_document_has_baseline_rules_and_identity() -> None:
    doc = build_starter_document(project="acme", languages=[])

    assert doc.project == "acme"
    assert doc.type == "agent"
    assert doc.agent is not None
    assert doc.agent.identity is not None
    assert doc.agent.identity.role == "Senior software engineer"
    # The identity ``context`` sentence is omitted when there is nothing
    # concrete to say (no domain, no languages).
    assert doc.agent.identity.context is None
    rule_ids = {rule.id for rule in doc.agent.rules}
    assert {"TDD-001", "SEC-001", "DOC-001"}.issubset(rule_ids)


def test_build_document_appends_language_rules_and_stack() -> None:
    doc = build_starter_document(
        project="church-manager",
        languages=["php", "symfony"],
        domain="parish management",
    )

    assert doc.agent is not None
    rule_ids = [rule.id for rule in doc.agent.rules]
    # Baseline appears first, then PHP, then Symfony.
    assert rule_ids[:3] == ["TDD-001", "SEC-001", "DOC-001"]
    assert "PHP-001" in rule_ids
    assert "SF-001" in rule_ids
    assert "SF-002" in rule_ids

    stack_required = doc.agent.stack.required if doc.agent.stack else []
    assert "php>=8.3" in stack_required
    assert "symfony>=7" in stack_required

    # Identity sentence wires the domain and the stack phrase together.
    assert doc.agent.identity is not None
    assert doc.agent.identity.context is not None
    assert "parish management" in doc.agent.identity.context
    assert "PHP" in doc.agent.identity.context
    assert "Symfony" in doc.agent.identity.context


def test_build_document_dedups_rule_ids() -> None:
    # Listing ``python`` twice should not duplicate PY-001 etc.
    doc = build_starter_document(project="x", languages=["python", "python"])
    assert doc.agent is not None
    ids = [rule.id for rule in doc.agent.rules]
    assert len(ids) == len(set(ids))


def test_build_document_round_trips_through_dump_and_parse() -> None:
    doc = build_starter_document(
        project="acme",
        languages=["typescript", "nextjs"],
        domain="fintech",
        title="Acme Console",
    )
    rendered = dump_ctx_string(doc)
    reparsed = parse_ctx_string(rendered)

    assert reparsed.project == doc.project
    assert reparsed.type == "agent"
    assert reparsed.agent is not None
    assert {rule.id for rule in reparsed.agent.rules} == {
        rule.id
        for rule in doc.agent.rules  # type: ignore[union-attr]
    }


def test_build_document_with_unknown_slug_is_a_noop() -> None:
    # Unknown slugs are silently ignored; the document still validates
    # because the baseline rules guarantee a non-empty rule list.
    doc = build_starter_document(project="x", languages=["does-not-exist"])
    assert doc.agent is not None
    rule_ids = {rule.id for rule in doc.agent.rules}
    assert rule_ids == {"TDD-001", "SEC-001", "DOC-001"}
    # Stack stays None because no language contributed anything.
    assert doc.agent.stack is None


def test_build_document_severity_strings_become_enum_members() -> None:
    doc = build_starter_document(project="x", languages=["python"])
    assert doc.agent is not None
    severities = {rule.severity for rule in doc.agent.rules}
    assert severities.issubset({Severity.MUST, Severity.SHOULD, Severity.MAY})


def test_build_document_role_override() -> None:
    doc = build_starter_document(
        project="x",
        languages=["python"],
        role="Staff backend engineer",
    )
    assert doc.agent is not None
    assert doc.agent.identity is not None
    assert doc.agent.identity.role == "Staff backend engineer"


def test_build_document_extra_stack_is_appended_after_language_stack() -> None:
    doc = build_starter_document(
        project="x",
        languages=["python"],
        extra_stack=["postgres>=16"],
    )
    assert doc.agent is not None
    assert doc.agent.stack is not None
    assert "python>=3.12" in doc.agent.stack.required
    assert "postgres>=16" in doc.agent.stack.required
