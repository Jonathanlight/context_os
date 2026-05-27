"""Tests for the AGENTS.md (codex) emitter."""

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
from contextos.emitters import emit_codex_markdown
from contextos.parsers import parse_markdown_string

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "codex"


def _doc(agent: AgentDocument | None = None, project: str = "Sample") -> Document:
    return Document(
        project=project,
        agent=agent if agent is not None else AgentDocument(),
    )


class TestProjectHeader:
    def test_emits_h1_with_project_name(self) -> None:
        out = emit_codex_markdown(_doc(project="MyBot"))
        assert out.startswith("# MyBot\n")

    def test_ends_with_single_trailing_newline(self) -> None:
        out = emit_codex_markdown(_doc(project="MyBot"))
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


class TestFlatStack:
    """Codex uses a flat bullet list under Stack — no H3 sub-sections."""

    def test_emits_flat_stack_from_required_only(self) -> None:
        agent = AgentDocument(stack=Stack(required=["python", "fastapi"]))
        out = emit_codex_markdown(_doc(agent))
        assert "## Stack\n\n- python\n- fastapi" in out
        # No H3 sub-headings.
        assert "### Required" not in out
        assert "### Forbidden" not in out

    def test_drops_forbidden_and_preferred_buckets(self) -> None:
        # Codex AGENTS.md cannot express forbidden / preferred. The emitter
        # silently drops them; this is the documented limitation.
        agent = AgentDocument(
            stack=Stack(
                required=["python"],
                forbidden=["django"],
                preferred=["fastapi"],
            )
        )
        out = emit_codex_markdown(_doc(agent))
        assert "## Stack\n\n- python" in out
        assert "django" not in out
        assert "fastapi" not in out

    def test_empty_required_collapses_section(self) -> None:
        agent = AgentDocument(stack=Stack(forbidden=["django"]))
        out = emit_codex_markdown(_doc(agent))
        assert "## Stack" not in out


class TestFlatTools:
    def test_emits_flat_tools(self) -> None:
        agent = AgentDocument(tools=Tools(required=["ruff", "mypy"]))
        out = emit_codex_markdown(_doc(agent))
        assert "## Tools\n\n- ruff\n- mypy" in out
        assert "### Required" not in out

    def test_drops_forbidden_tools(self) -> None:
        agent = AgentDocument(tools=Tools(required=["ruff"], forbidden=["black"]))
        out = emit_codex_markdown(_doc(agent))
        assert "## Tools\n\n- ruff" in out
        assert "black" not in out

    def test_empty_required_collapses_section(self) -> None:
        agent = AgentDocument(tools=Tools(forbidden=["black"]))
        out = emit_codex_markdown(_doc(agent))
        assert "## Tools" not in out


class TestRulesWithSeverity:
    def test_each_rule_becomes_a_bullet(self) -> None:
        rules = [
            Rule(id="A-001", title="First rule", severity=Severity.MUST),
            Rule(id="A-002", title="Second rule", severity=Severity.SHOULD),
        ]
        out = emit_codex_markdown(_doc(AgentDocument(rules=rules)))
        assert "- Must first rule." in out
        assert "- Should second rule." in out

    def test_severity_leading_word_kept(self) -> None:
        rules = [
            Rule(id="A-001", title="Never commit secrets", severity=Severity.MUST),
            Rule(id="A-002", title="May add docstrings", severity=Severity.MAY),
        ]
        out = emit_codex_markdown(_doc(AgentDocument(rules=rules)))
        assert "- Never commit secrets." in out
        assert "- May add docstrings." in out


class TestSectionOrder:
    def test_canonical_section_order(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="single maintainer"),
            stack=Stack(required=["python"]),
            rules=[Rule(id="X-001", title="Use type hints", severity=Severity.MUST)],
            style=Style(conventions=["4 spaces"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff"]),
        )
        out = emit_codex_markdown(_doc(agent))
        indices = [
            out.index("## Identity"),
            out.index("## Stack"),
            out.index("## Rules"),
            out.index("## Style"),
            out.index("## Forbidden patterns"),
            out.index("## Tools"),
        ]
        assert indices == sorted(indices)


class TestByteStability:
    def test_same_doc_produces_same_output(self) -> None:
        agent = AgentDocument(
            stack=Stack(required=["python"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        doc = _doc(agent)
        assert emit_codex_markdown(doc) == emit_codex_markdown(doc)

    def test_no_trailing_whitespace_per_line(self) -> None:
        agent = AgentDocument(
            stack=Stack(required=["x"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        out = emit_codex_markdown(_doc(agent))
        for line in out.splitlines():
            assert not line.endswith(" "), f"trailing whitespace on line: {line!r}"


class TestSnapshotMinimal:
    def test_minimal_snapshot(self) -> None:
        out = emit_codex_markdown(_doc(project="MyBot"))
        assert out == "# MyBot\n"

    def test_full_snapshot(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="single maintainer"),
            stack=Stack(required=["python>=3.12", "asyncio"]),
            rules=[
                Rule(id="A-001", title="Never commit secrets", severity=Severity.MUST),
                Rule(id="A-002", title="Sanitize input", severity=Severity.SHOULD),
            ],
            style=Style(conventions=["4 spaces", "snake_case"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff", "mypy"]),
        )
        expected = textwrap.dedent(
            """\
            # MyBot

            ## Identity

            single maintainer

            ## Stack

            - python>=3.12
            - asyncio

            ## Rules

            - Never commit secrets.
            - Should sanitize input.

            ## Style

            - 4 spaces
            - snake_case

            ## Forbidden patterns

            - wildcard imports

            ## Tools

            - ruff
            - mypy
            """
        )
        assert emit_codex_markdown(_doc(agent, project="MyBot")) == expected


class TestRoundTripCodex:
    """parse_markdown(emit_codex(doc), 'codex') preserves what codex can carry."""

    @pytest.mark.parametrize("fixture_name", ["minimal", "full"])
    def test_fixture_round_trips(self, fixture_name: str) -> None:
        path = FIXTURES_DIR / f"{fixture_name}.md"
        original = parse_markdown_string(path.read_text(), target="codex")
        emitted = emit_codex_markdown(original)
        reparsed = parse_markdown_string(emitted, target="codex")
        assert reparsed.project == original.project
        assert original.agent is not None
        assert reparsed.agent is not None
        assert len(reparsed.agent.rules) == len(original.agent.rules)
        for orig, back in zip(original.agent.rules, reparsed.agent.rules, strict=False):
            assert orig.severity == back.severity
