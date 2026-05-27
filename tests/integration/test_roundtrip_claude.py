"""Round-trip property tests for the Phase 1 deliverable.

Two properties exercised by hypothesis-generated documents:

- ``emit-then-parse`` preserves the semantic content of a Document modulo
  the fields the Markdown bullet format cannot carry (Rule.id, rationale,
  tags, etc.). Compared after :func:`_normalize`, the original and the
  re-parsed Document must be equal.
- ``emit → parse → emit`` is byte-stable. The second emit must equal the
  first to the byte; this is the strong idempotence property the SPEC
  calls out for the agent emitter.

These two together pin down what "the Claude emitter works" means for
Milestone 1.6 and gate Phase 1 closure.
"""

from __future__ import annotations

import string
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

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
from contextos.parsers import parse_markdown_string

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Keep generated strings within a safe subset:
# - Letters + spaces only — no markdown metacharacters (#, -, *, |, [, ]),
#   no TOML metacharacters (", ', =, [, ], \\), no newlines, no tabs.
# - Bounded length so the generator finishes 1000 iterations in seconds.
_SAFE_ALPHABET = string.ascii_letters + " "

_safe_text = st.text(alphabet=_SAFE_ALPHABET, min_size=1, max_size=30).map(str.strip).filter(bool)

_severity_st = st.sampled_from([Severity.MUST, Severity.SHOULD, Severity.MAY])

_rule_id_st = st.builds(
    lambda prefix, number: f"{prefix}-{number:03d}",
    prefix=st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=5),
    number=st.integers(min_value=0, max_value=999),
)

_rule_st = st.builds(
    Rule,
    id=_rule_id_st,
    title=_safe_text,
    severity=_severity_st,
)

_identity_st = st.builds(Identity, role=_safe_text)

_stack_st = st.builds(
    Stack,
    required=st.lists(_safe_text, max_size=4),
    forbidden=st.lists(_safe_text, max_size=4),
    preferred=st.lists(_safe_text, max_size=4),
)

_style_st = st.builds(Style, conventions=st.lists(_safe_text, max_size=4))

_tools_st = st.builds(
    Tools,
    required=st.lists(_safe_text, max_size=4),
    forbidden=st.lists(_safe_text, max_size=4),
)

_agent_st = st.builds(
    AgentDocument,
    identity=st.one_of(st.none(), _identity_st),
    stack=st.one_of(st.none(), _stack_st),
    style=st.one_of(st.none(), _style_st),
    tools=st.one_of(st.none(), _tools_st),
    rules=st.lists(_rule_st, max_size=5),
    forbidden_patterns=st.lists(_safe_text, max_size=4),
)


def arbitrary_document() -> st.SearchStrategy[Document]:
    """Hypothesis strategy for a context-family Document.

    The generated documents stay within what the bullet-rule Markdown
    format can faithfully represent: no special characters, bounded
    sizes, and the agent slot always populated.
    """
    return st.builds(
        lambda project, agent: Document(project=project, agent=agent),
        project=_safe_text,
        agent=_agent_st,
    )


# ---------------------------------------------------------------------------
# Semantic equivalence
# ---------------------------------------------------------------------------


def _normalize(doc: Document) -> dict[str, Any]:
    """Project a Document down to the fields preserved by emit→parse.

    Drops:
    - Empty lists and empty sub-models (treat absence == empty)
    - Rule.id, rationale, detail, examples, tags, links, position,
      applies_to (all lost by the bullet format)
    - Document.ctx_version, languages, authors, version (not emitted)
    - Rule.title (modified by severity prefixing; compare severity only)
    """
    norm: dict[str, Any] = {"project": doc.project}
    agent = doc.agent
    if agent is None:
        return norm

    if agent.identity is not None and agent.identity.role:
        norm["identity"] = agent.identity.role
    _set_if_truthy(norm, "stack", _normalize_stack(agent.stack))
    if agent.style is not None and agent.style.conventions:
        norm["style"] = list(agent.style.conventions)
    _set_if_truthy(norm, "tools", _normalize_tools(agent.tools))
    if agent.forbidden_patterns:
        norm["forbidden_patterns"] = list(agent.forbidden_patterns)
    if agent.rules:
        # Rule.title is modified by severity prefixing across the round-trip,
        # so we compare only the sequence of severities (which IS preserved).
        norm["rule_severities"] = [r.severity.value for r in agent.rules]
    return norm


def _normalize_stack(stack: Stack | None) -> dict[str, list[str]]:
    """Collapse a Stack into the populated buckets only (empty → dropped)."""
    if stack is None:
        return {}
    out: dict[str, list[str]] = {}
    if stack.required:
        out["required"] = list(stack.required)
    if stack.forbidden:
        out["forbidden"] = list(stack.forbidden)
    if stack.preferred:
        out["preferred"] = list(stack.preferred)
    return out


def _normalize_tools(tools: Tools | None) -> dict[str, list[str]]:
    """Collapse a Tools into the populated buckets only."""
    if tools is None:
        return {}
    out: dict[str, list[str]] = {}
    if tools.required:
        out["required"] = list(tools.required)
    if tools.forbidden:
        out["forbidden"] = list(tools.forbidden)
    return out


def _set_if_truthy(target: dict[str, Any], key: str, value: Any) -> None:
    if value:
        target[key] = value


def assert_semantically_equivalent(original: Document, reparsed: Document) -> None:
    """Compare two Documents modulo lossy fields and empty-vs-None."""
    assert _normalize(original) == _normalize(reparsed), (
        f"semantic drift across round-trip:\n"
        f"  original:  {_normalize(original)}\n"
        f"  reparsed:  {_normalize(reparsed)}"
    )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(arbitrary_document())
@settings(max_examples=1000, deadline=None)
def test_emit_then_parse_is_semantically_equivalent(doc: Document) -> None:
    """``parse_markdown(emit_claude(doc))`` preserves the semantic shape."""
    emitted = emit_claude_markdown(doc)
    reparsed = parse_markdown_string(emitted, target="claude_code")
    assert_semantically_equivalent(doc, reparsed)


@given(arbitrary_document())
@settings(max_examples=200, deadline=None)
def test_emit_is_idempotent_after_one_round_trip(doc: Document) -> None:
    """``emit(parse(emit(doc))) == emit(doc)``: the second emit is byte-stable."""
    first = emit_claude_markdown(doc)
    reparsed = parse_markdown_string(first, target="claude_code")
    second = emit_claude_markdown(reparsed)
    assert first == second, (
        f"emit drifted after one round-trip:\n---first---\n{first}\n---second---\n{second}\n---"
    )


# ---------------------------------------------------------------------------
# Sanity tests on _normalize (so a broken helper does not hide drift)
# ---------------------------------------------------------------------------


def test_normalize_treats_empty_stack_as_absent() -> None:
    doc_with = Document(
        project="P",
        agent=AgentDocument(stack=Stack()),
    )
    doc_without = Document(project="P", agent=AgentDocument())
    assert _normalize(doc_with) == _normalize(doc_without)


def test_normalize_drops_lossy_fields() -> None:
    doc_a = Document(
        project="P",
        agent=AgentDocument(
            rules=[
                Rule(
                    id="A-001",
                    title="t",
                    severity=Severity.MUST,
                    rationale="why",
                    tags=["x"],
                )
            ],
        ),
    )
    doc_b = Document(
        project="P",
        agent=AgentDocument(
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        ),
    )
    assert _normalize(doc_a) == _normalize(doc_b)


def test_normalize_detects_severity_drift() -> None:
    doc_a = Document(
        project="P",
        agent=AgentDocument(
            rules=[Rule(id="A-001", title="t", severity=Severity.MUST)],
        ),
    )
    doc_b = Document(
        project="P",
        agent=AgentDocument(
            rules=[Rule(id="A-001", title="t", severity=Severity.SHOULD)],
        ),
    )
    assert _normalize(doc_a) != _normalize(doc_b)


def test_normalize_detects_project_drift() -> None:
    doc_a = Document(project="A", agent=AgentDocument())
    doc_b = Document(project="B", agent=AgentDocument())
    assert _normalize(doc_a) != _normalize(doc_b)
