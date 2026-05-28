"""Tests for the flat-Markdown agent emitters (copilot / cline / windsurf).

Three targets, one shared implementation (``_agent_base.emit_flat_agent_markdown``).
The wrappers must produce identical bytes for the same Document; the test
suite asserts that explicitly and checks the published shape on a snapshot.
"""

from __future__ import annotations

import textwrap

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
from contextos.emitters import (
    emit_clinerules,
    emit_copilot_instructions,
    emit_windsurfrules,
)


def _doc(agent: AgentDocument | None = None, project: str = "Sample") -> Document:
    return Document(
        project=project,
        agent=agent if agent is not None else AgentDocument(),
    )


# Every wrapper produces the same output for the same Document.
_WRAPPERS = (emit_copilot_instructions, emit_clinerules, emit_windsurfrules)


class TestWrappersShareImplementation:
    def test_wrappers_emit_identical_bytes(self) -> None:
        """Same Document -> same emitted Markdown across all three wrappers."""
        agent = AgentDocument(
            identity=Identity(role="senior engineer"),
            stack=Stack(required=["python>=3.12"]),
            rules=[Rule(id="A-001", title="Use type hints", severity=Severity.MUST)],
            style=Style(conventions=["4 spaces"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff"]),
        )
        doc = _doc(agent, project="MyApp")
        outputs = [wrapper(doc) for wrapper in _WRAPPERS]
        assert outputs[0] == outputs[1] == outputs[2]


@pytest.mark.parametrize("wrapper", _WRAPPERS)
class TestFlatLayout:
    """Each wrapper individually honors the flat-Markdown contract."""

    def test_h1_with_project_name(self, wrapper: object) -> None:
        out = wrapper(_doc(project="MyApp"))  # type: ignore[operator]
        assert out.startswith("# MyApp\n")

    def test_trailing_newline(self, wrapper: object) -> None:
        out = wrapper(_doc())  # type: ignore[operator]
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_no_per_line_trailing_whitespace(self, wrapper: object) -> None:
        agent = AgentDocument(
            stack=Stack(required=["python"]),
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        )
        for line in wrapper(_doc(agent)).splitlines():  # type: ignore[operator]
            assert not line.endswith(" ")

    def test_flat_stack(self, wrapper: object) -> None:
        agent = AgentDocument(stack=Stack(required=["python", "fastapi"]))
        out = wrapper(_doc(agent))  # type: ignore[operator]
        assert "## Stack\n\n- python\n- fastapi" in out
        # No H3 sub-headings.
        assert "### Required" not in out

    def test_drops_stack_forbidden_and_preferred(self, wrapper: object) -> None:
        agent = AgentDocument(
            stack=Stack(
                required=["python"],
                forbidden=["django"],
                preferred=["fastapi"],
            )
        )
        out = wrapper(_doc(agent))  # type: ignore[operator]
        assert "## Stack\n\n- python" in out
        assert "django" not in out
        assert "fastapi" not in out

    def test_flat_tools(self, wrapper: object) -> None:
        agent = AgentDocument(tools=Tools(required=["ruff"]))
        out = wrapper(_doc(agent))  # type: ignore[operator]
        assert "## Tools\n\n- ruff" in out
        assert "### Required" not in out

    def test_severity_prefix_preserved(self, wrapper: object) -> None:
        rules = [
            Rule(id="A-001", title="First rule", severity=Severity.MUST),
            Rule(id="A-002", title="Second rule", severity=Severity.SHOULD),
        ]
        out = wrapper(_doc(AgentDocument(rules=rules)))  # type: ignore[operator]
        assert "- Must first rule." in out
        assert "- Should second rule." in out


class TestSnapshot:
    """A representative Document yields the exact same Markdown across wrappers."""

    def _full_doc(self) -> Document:
        agent = AgentDocument(
            identity=Identity(role="single maintainer"),
            stack=Stack(required=["python>=3.12"]),
            rules=[
                Rule(id="A-001", title="Never commit secrets", severity=Severity.MUST),
                Rule(id="A-002", title="Sanitize input", severity=Severity.SHOULD),
            ],
            style=Style(conventions=["4 spaces"]),
            forbidden_patterns=["wildcard imports"],
            tools=Tools(required=["ruff"]),
        )
        return _doc(agent, project="MyBot")

    def test_snapshot_is_canonical(self) -> None:
        expected = textwrap.dedent(
            """\
            # MyBot

            ## Identity

            single maintainer

            ## Stack

            - python>=3.12

            ## Rules

            - Never commit secrets.
            - Should sanitize input.

            ## Style

            - 4 spaces

            ## Forbidden patterns

            - wildcard imports

            ## Tools

            - ruff
            """
        )
        for wrapper in _WRAPPERS:
            assert wrapper(self._full_doc()) == expected
