"""Tests for the Cursor ``.mdc`` emitter."""

from __future__ import annotations

import textwrap

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
from contextos.emitters import emit_cursor_mdc


def _doc(agent: AgentDocument | None = None, project: str = "Sample") -> Document:
    return Document(
        project=project,
        agent=agent if agent is not None else AgentDocument(),
    )


class TestFrontmatter:
    def test_starts_with_yaml_frontmatter(self) -> None:
        out = emit_cursor_mdc(_doc(project="MyApp"))
        lines = out.splitlines()
        assert lines[0] == "---"
        # description / globs / alwaysApply / closing ---
        assert lines[4] == "---"

    def test_description_mentions_project(self) -> None:
        out = emit_cursor_mdc(_doc(project="MyApp"))
        assert "description: Rules for MyApp" in out

    def test_description_appends_identity_role(self) -> None:
        agent = AgentDocument(identity=Identity(role="senior engineer"))
        out = emit_cursor_mdc(_doc(agent, project="MyApp"))
        assert "description: Rules for MyApp — senior engineer" in out

    def test_globs_and_always_apply_present(self) -> None:
        out = emit_cursor_mdc(_doc())
        assert 'globs: ["**/*"]' in out
        assert "alwaysApply: true" in out


class TestAllCapsSections:
    def test_identity_section_when_present(self) -> None:
        agent = AgentDocument(identity=Identity(role="senior engineer"))
        out = emit_cursor_mdc(_doc(agent))
        # Body section uses ALL-CAPS, not `## Markdown`.
        assert "IDENTITY\nsenior engineer" in out
        assert "## Identity" not in out

    def test_no_identity_when_absent(self) -> None:
        out = emit_cursor_mdc(_doc())
        assert "IDENTITY" not in out

    def test_stack_required_emits_bullets(self) -> None:
        agent = AgentDocument(stack=Stack(required=["python", "fastapi"]))
        out = emit_cursor_mdc(_doc(agent))
        assert "TECHNOLOGY STACK\n- python\n- fastapi" in out

    def test_stack_forbidden_and_preferred_are_dropped(self) -> None:
        agent = AgentDocument(
            stack=Stack(
                required=["python"],
                forbidden=["django"],
                preferred=["fastapi"],
            )
        )
        out = emit_cursor_mdc(_doc(agent))
        assert "TECHNOLOGY STACK\n- python" in out
        assert "django" not in out
        assert "fastapi" not in out

    def test_rules_become_bullet_list(self) -> None:
        rules = [
            Rule(id="A-001", title="First", severity=Severity.MUST),
            Rule(id="A-002", title="Second", severity=Severity.SHOULD),
        ]
        out = emit_cursor_mdc(_doc(AgentDocument(rules=rules)))
        assert "ASSISTANT RULES\n- Must first.\n- Should second." in out

    def test_style_section(self) -> None:
        agent = AgentDocument(style=Style(conventions=["4 spaces", "snake_case"]))
        out = emit_cursor_mdc(_doc(agent))
        assert "CODING STYLE\n- 4 spaces\n- snake_case" in out

    def test_forbidden_section(self) -> None:
        agent = AgentDocument(forbidden_patterns=["wildcard imports"])
        out = emit_cursor_mdc(_doc(agent))
        assert "FORBIDDEN PATTERNS\n- wildcard imports" in out

    def test_tools_required_only(self) -> None:
        agent = AgentDocument(tools=Tools(required=["ruff"], forbidden=["black"]))
        out = emit_cursor_mdc(_doc(agent))
        assert "TOOLING\n- ruff" in out
        assert "black" not in out


class TestSectionOrder:
    def test_canonical_order(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="r"),
            stack=Stack(required=["python"]),
            rules=[Rule(id="X-001", title="t", severity=Severity.MUST)],
            style=Style(conventions=["c"]),
            forbidden_patterns=["p"],
            tools=Tools(required=["ruff"]),
        )
        out = emit_cursor_mdc(_doc(agent))
        indices = [
            out.index("IDENTITY"),
            out.index("TECHNOLOGY STACK"),
            out.index("ASSISTANT RULES"),
            out.index("CODING STYLE"),
            out.index("FORBIDDEN PATTERNS"),
            out.index("TOOLING"),
        ]
        assert indices == sorted(indices)


class TestEmptySections:
    def test_empty_agent_emits_only_frontmatter(self) -> None:
        out = emit_cursor_mdc(_doc())
        body_after_frontmatter = out.split("---\n", 2)[-1].strip()
        assert body_after_frontmatter == ""

    def test_stack_with_no_required_collapses_section(self) -> None:
        agent = AgentDocument(stack=Stack(forbidden=["django"]))
        out = emit_cursor_mdc(_doc(agent))
        assert "TECHNOLOGY STACK" not in out

    def test_empty_style_collapses(self) -> None:
        agent = AgentDocument(style=Style())
        out = emit_cursor_mdc(_doc(agent))
        assert "CODING STYLE" not in out


class TestByteStability:
    def test_same_doc_produces_same_output(self) -> None:
        agent = AgentDocument(
            stack=Stack(required=["python"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        doc = _doc(agent)
        assert emit_cursor_mdc(doc) == emit_cursor_mdc(doc)

    def test_trailing_newline(self) -> None:
        out = emit_cursor_mdc(_doc())
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_no_per_line_trailing_whitespace(self) -> None:
        agent = AgentDocument(
            stack=Stack(required=["python"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        for line in emit_cursor_mdc(_doc(agent)).splitlines():
            assert not line.endswith(" ")


class TestSnapshotMinimal:
    def test_minimal_snapshot(self) -> None:
        expected = textwrap.dedent(
            """\
            ---
            description: Rules for MyApp
            globs: ["**/*"]
            alwaysApply: true
            ---
            """
        )
        assert emit_cursor_mdc(_doc(project="MyApp")) == expected

    def test_full_snapshot(self) -> None:
        agent = AgentDocument(
            identity=Identity(role="senior engineer"),
            stack=Stack(required=["python>=3.12"]),
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
            ---
            description: Rules for MyApp — senior engineer
            globs: ["**/*"]
            alwaysApply: true
            ---

            IDENTITY
            senior engineer

            TECHNOLOGY STACK
            - python>=3.12

            ASSISTANT RULES
            - Never commit secrets.
            - Should sanitize input.

            CODING STYLE
            - 4 spaces
            - snake_case

            FORBIDDEN PATTERNS
            - wildcard imports

            TOOLING
            - ruff
            - mypy
            """
        )
        assert emit_cursor_mdc(_doc(agent, project="MyApp")) == expected
