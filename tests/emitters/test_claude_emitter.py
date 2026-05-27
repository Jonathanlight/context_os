"""Tests for the CLAUDE.md emitter (Milestone 1.5)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

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
from contextos.emitters import emit_claude_markdown
from contextos.parsers import parse_ctx_file, parse_markdown_string

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "ctx" / "valid"


def _make_doc(agent: AgentDocument | None = None, project: str = "Sample") -> Document:
    return Document(project=project, agent=agent if agent is not None else AgentDocument())


class TestProjectHeader:
    def test_emits_h1_with_project_name(self) -> None:
        out = emit_claude_markdown(_make_doc(project="MyApp"))
        assert out.startswith("# MyApp\n")

    def test_ends_with_single_trailing_newline(self) -> None:
        out = emit_claude_markdown(_make_doc(project="MyApp"))
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


class TestEmptyAgent:
    def test_no_sections_when_agent_is_empty(self) -> None:
        out = emit_claude_markdown(_make_doc())
        assert out == "# Sample\n"

    def test_no_agent_at_all(self) -> None:
        # Document with agent=None — the Document validator would reject this
        # at construction, so we test the emit-side defensively only.
        # Build via a valid doc first then bypass via model_construct.
        doc = Document.model_construct(project="P", type="agent", agent=None)
        assert emit_claude_markdown(doc) == "# P\n"


class TestSectionOrder:
    def test_sections_appear_in_canonical_order(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="senior"),
            stack=Stack(required=["python"]),
            rules=[Rule(id="X-001", title="Use type hints", severity=Severity.MUST)],
            style=Style(conventions=["4 spaces"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff"]),
        )
        out = emit_claude_markdown(_make_doc(agent))
        indices = [
            out.index("## Identity"),
            out.index("## Stack"),
            out.index("## Rules"),
            out.index("## Style"),
            out.index("## Forbidden patterns"),
            out.index("## Tools"),
        ]
        assert indices == sorted(indices)


class TestIdentitySection:
    def test_omitted_when_none(self) -> None:
        agent = AgentDocument(rules=[Rule(id="X-001", title="t", severity=Severity.MUST)])
        out = emit_claude_markdown(_make_doc(agent))
        assert "## Identity" not in out

    def test_emits_role_paragraph(self) -> None:
        agent = AgentDocument(identity=Identity(role="senior engineer"))
        out = emit_claude_markdown(_make_doc(agent))
        assert "## Identity\n\nsenior engineer\n" in out


class TestStackSection:
    def test_omits_empty_sub_sections(self) -> None:
        agent = AgentDocument(stack=Stack(required=["python"]))
        out = emit_claude_markdown(_make_doc(agent))
        assert "### Required" in out
        assert "### Forbidden" not in out
        assert "### Preferred" not in out

    def test_emits_three_sub_sections_when_populated(self) -> None:
        agent = AgentDocument(
            stack=Stack(
                required=["python", "fastapi"],
                forbidden=["django"],
                preferred=["uvloop"],
            )
        )
        out = emit_claude_markdown(_make_doc(agent))
        for h3 in ("### Required", "### Forbidden", "### Preferred"):
            assert h3 in out
        # Bullets appear in order.
        assert out.index("- python") < out.index("- fastapi")


class TestRulesSection:
    def test_each_rule_becomes_a_bullet(self) -> None:
        rules = [
            Rule(id="A-001", title="First rule", severity=Severity.MUST),
            Rule(id="A-002", title="Second rule", severity=Severity.SHOULD),
        ]
        agent = AgentDocument(rules=rules)
        out = emit_claude_markdown(_make_doc(agent))
        assert "- Must first rule." in out
        assert "- Should second rule." in out

    def test_severity_leading_word_kept(self) -> None:
        rules = [
            Rule(id="A-001", title="Never commit secrets", severity=Severity.MUST),
            Rule(id="A-002", title="Should prefer composition", severity=Severity.SHOULD),
            Rule(id="A-003", title="May add docstrings", severity=Severity.MAY),
        ]
        agent = AgentDocument(rules=rules)
        out = emit_claude_markdown(_make_doc(agent))
        assert "- Never commit secrets." in out
        assert "- Should prefer composition." in out
        assert "- May add docstrings." in out

    def test_severity_prefix_added_when_missing(self) -> None:
        rules = [Rule(id="A-001", title="Use type hints", severity=Severity.SHOULD)]
        agent = AgentDocument(rules=rules)
        out = emit_claude_markdown(_make_doc(agent))
        assert "- Should use type hints." in out


class TestForbiddenAndTools:
    def test_forbidden_patterns_bullets(self) -> None:
        agent = AgentDocument(forbidden_patterns=["wildcard imports", "raw SQL"])
        out = emit_claude_markdown(_make_doc(agent))
        assert "## Forbidden patterns\n\n- wildcard imports\n- raw SQL" in out

    def test_tools_sub_sections(self) -> None:
        agent = AgentDocument(tools=Tools(required=["ruff", "mypy"], forbidden=["black"]))
        out = emit_claude_markdown(_make_doc(agent))
        assert "## Tools" in out
        assert "### Required" in out
        assert "### Forbidden" in out
        assert "- ruff" in out
        assert "- black" in out

    def test_style_bullets(self) -> None:
        agent = AgentDocument(style=Style(conventions=["4 spaces", "snake_case"]))
        out = emit_claude_markdown(_make_doc(agent))
        assert "## Style\n\n- 4 spaces\n- snake_case" in out


class TestByteStability:
    def test_same_doc_produces_same_output(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="x"),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        doc = _make_doc(agent)
        first = emit_claude_markdown(doc)
        second = emit_claude_markdown(doc)
        assert first == second

    def test_no_trailing_whitespace_per_line(self) -> None:
        agent = AgentDocument(
            stack=Stack(required=["x"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        out = emit_claude_markdown(_make_doc(agent))
        for line in out.splitlines():
            assert not line.endswith(" "), f"trailing whitespace on line: {line!r}"


class TestSnapshotMinimal:
    def test_minimal_snapshot(self) -> None:
        doc = _make_doc(project="MyApp")
        expected = "# MyApp\n"
        assert emit_claude_markdown(doc) == expected

    def test_full_snapshot(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="senior engineer"),
            stack=Stack(
                required=["python>=3.12"],
                forbidden=["django"],
                preferred=["fastapi"],
            ),
            rules=[
                Rule(id="TDD-001", title="Never commit secrets", severity=Severity.MUST),
                Rule(id="SEC-042", title="Sanitize input", severity=Severity.SHOULD),
            ],
            style=Style(conventions=["4 spaces", "snake_case"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff"], forbidden=["black"]),
        )
        doc = _make_doc(agent, project="MyApp")
        expected = textwrap.dedent(
            """\
            # MyApp

            ## Identity

            senior engineer

            ## Stack

            ### Required

            - python>=3.12

            ### Forbidden

            - django

            ### Preferred

            - fastapi

            ## Rules

            - Never commit secrets.
            - Should sanitize input.

            ## Style

            - 4 spaces
            - snake_case

            ## Forbidden patterns

            - wildcard imports

            ## Tools

            ### Required

            - ruff

            ### Forbidden

            - black
            """
        )
        assert emit_claude_markdown(doc) == expected


class TestFromCtxFixtures:
    """Emit Documents produced by the .ctx parser; assert semantic invariants."""

    @pytest.mark.parametrize(
        "fixture_name",
        ["minimal", "full", "only_rules", "identity_only"],
    )
    def test_emit_round_trip_parseable_back(self, fixture_name: str) -> None:
        """parse(.ctx) -> emit -> parse(markdown) yields a Document with the
        same project name and the same rule count, modulo lossy fields.
        """
        path = FIXTURES_DIR / f"{fixture_name}.ctx"
        original = parse_ctx_file(path)
        emitted = emit_claude_markdown(original)
        reparsed = parse_markdown_string(emitted, target="claude_code")

        assert reparsed.project == original.project
        if original.agent is not None and reparsed.agent is not None:
            assert len(reparsed.agent.rules) == len(original.agent.rules)
            # Severity is preserved through the round-trip (via leading-word
            # prefixing in the emitter).
            for orig, back in zip(original.agent.rules, reparsed.agent.rules, strict=False):
                assert orig.severity == back.severity, (
                    f"severity drift on '{orig.title}': {orig.severity} -> {back.severity}"
                )
