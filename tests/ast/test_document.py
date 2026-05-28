"""Tests for the root Document model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.ast.agent import AgentDocument, Identity, Rule
from contextos.ast.common import Severity
from contextos.ast.document import CTX_VERSION, Document
from contextos.ast.skill import SkillDocument


class TestDocument:
    def test_minimal_agent_document(self) -> None:
        doc = Document(project="MyApp", agent=AgentDocument())
        assert doc.project == "MyApp"
        assert doc.type == "agent"
        assert doc.ctx_version == CTX_VERSION
        assert doc.version == "0.1.0"
        assert doc.languages == []
        assert doc.authors == []

    def test_full_agent_document(self) -> None:
        doc = Document(
            project="MyApp",
            ctx_version="0.3",
            type="agent",
            languages=["Python", "Rust"],
            authors=["Jonathan KABLAN"],
            version="1.2.3",
            agent=AgentDocument(
                identity=Identity(role="senior"),
                rules=[Rule(id="TDD-001", title="t", severity=Severity.MUST)],
            ),
        )
        assert doc.languages == ["Python", "Rust"]
        assert doc.version == "1.2.3"
        assert doc.agent is not None
        assert len(doc.agent.rules) == 1

    def test_project_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            Document(project="", agent=AgentDocument())

    def test_type_agent_requires_agent_slot(self) -> None:
        with pytest.raises(ValidationError, match=r"requires Document\.agent"):
            Document(project="MyApp", type="agent", agent=None)

    def test_rejects_unknown_type(self) -> None:
        # Phase 6 will widen the literal to admit "rag"; until then it must reject.
        with pytest.raises(ValidationError):
            Document.model_validate(
                {
                    "project": "MyApp",
                    "type": "rag",
                    "agent": {},
                }
            )

    def test_agent_type_rejects_stray_skill_payload(self) -> None:
        skill = SkillDocument(
            name="pdf-extract",
            title="t",
            description="Extract text from PDFs when the user asks.",
        )
        with pytest.raises(ValidationError, match=r"must not carry a skill payload"):
            Document(
                project="X",
                type="agent",
                agent=AgentDocument(),
                skill=skill,
            )

    def test_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Document.model_validate(
                {
                    "project": "MyApp",
                    "agent": {},
                    "tags": ["x"],
                }
            )

    def test_round_trips_via_json(self) -> None:
        original = Document(
            project="MyApp",
            languages=["Python"],
            authors=["Jonathan KABLAN"],
            agent=AgentDocument(
                rules=[Rule(id="TDD-001", title="t", severity=Severity.MUST)],
            ),
        )
        restored = Document.model_validate_json(original.model_dump_json())
        assert restored == original

    def test_round_trips_via_dict(self) -> None:
        original = Document(project="X", agent=AgentDocument())
        restored = Document.model_validate(original.model_dump())
        assert restored == original

    def test_ctx_version_defaults_to_current(self) -> None:
        doc = Document(project="X", agent=AgentDocument())
        assert doc.ctx_version == "0.3"
