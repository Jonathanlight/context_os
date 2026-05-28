"""Tests for the EvalSuite AST node — Phase 7.7."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from contextos.ast.eval import EvalSuite, RagCase, SkillCase


def _skill_case(**overrides: object) -> SkillCase:
    payload: dict[str, object] = {
        "name": "happy-path",
        "prompt": "Extract the line items from this invoice.pdf",
        "expected_skill": "pdf-extract",
    }
    payload.update(overrides)
    return SkillCase.model_validate(payload)


def _rag_case(**overrides: object) -> RagCase:
    payload: dict[str, object] = {
        "name": "vacation-policy",
        "query": "What is the maximum vacation balance?",
        "expected_sources": ["docs/policies/vacation.md"],
    }
    payload.update(overrides)
    return RagCase.model_validate(payload)


class TestSkillCase:
    def test_minimal_case(self) -> None:
        case = _skill_case()
        assert case.name == "happy-path"
        assert case.expected_skill == "pdf-extract"
        assert case.tags == []

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _skill_case(name="")

    def test_empty_prompt_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _skill_case(prompt="")

    def test_empty_expected_skill_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _skill_case(expected_skill="")

    def test_tags_preserved(self) -> None:
        case = _skill_case(tags=["fr", "happy-path"])
        assert case.tags == ["fr", "happy-path"]

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SkillCase.model_validate(
                {
                    "name": "x",
                    "prompt": "y",
                    "expected_skill": "z",
                    "mystery": "nope",
                }
            )


class TestRagCase:
    def test_minimal_case(self) -> None:
        case = _rag_case()
        assert case.top_k == 5
        assert case.expected_sources == ["docs/policies/vacation.md"]

    def test_top_k_bounds(self) -> None:
        assert _rag_case(top_k=1).top_k == 1
        assert _rag_case(top_k=100).top_k == 100
        with pytest.raises(ValidationError):
            _rag_case(top_k=0)
        with pytest.raises(ValidationError):
            _rag_case(top_k=101)

    def test_expected_sources_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            _rag_case(expected_sources=[])

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _rag_case(query="")


class TestEvalSuiteSkillTarget:
    def test_minimal_skill_suite(self) -> None:
        suite = EvalSuite(
            project="X",
            target="anthropic_skill",
            skill_cases=[_skill_case()],
        )
        assert suite.total_cases() == 1
        assert suite.target == "anthropic_skill"

    def test_skill_target_with_rag_cases_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry rag_cases"):
            EvalSuite(
                project="X",
                target="anthropic_skill",
                skill_cases=[_skill_case()],
                rag_cases=[_rag_case()],
            )

    def test_skill_target_with_rag_cases_only_rejected(self) -> None:
        # Sneaky case: target says skill but only rag_cases populated.
        with pytest.raises(ValidationError, match=r"must not carry rag_cases"):
            EvalSuite(
                project="X",
                target="anthropic_skill",
                rag_cases=[_rag_case()],
            )


class TestEvalSuiteRagTarget:
    def test_minimal_rag_suite(self) -> None:
        suite = EvalSuite(
            project="X",
            target="rag",
            rag_cases=[_rag_case()],
        )
        assert suite.total_cases() == 1
        assert suite.target == "rag"

    def test_rag_target_with_skill_cases_rejected(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry skill_cases"):
            EvalSuite(
                project="X",
                target="rag",
                rag_cases=[_rag_case()],
                skill_cases=[_skill_case()],
            )


class TestEvalSuiteCommon:
    def test_unknown_target_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvalSuite.model_validate(
                {
                    "project": "X",
                    "target": "claude_code",
                    "skill_cases": [],
                }
            )

    def test_empty_suite_accepted(self) -> None:
        # An empty suite (no cases) is a valid placeholder.
        suite = EvalSuite(project="X", target="anthropic_skill")
        assert suite.total_cases() == 0

    def test_default_suite_version(self) -> None:
        suite = EvalSuite(project="X", target="rag")
        assert suite.suite_version == "1.0"

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EvalSuite.model_validate(
                {
                    "project": "X",
                    "target": "rag",
                    "future_field": True,
                }
            )

    def test_round_trip_via_dict(self) -> None:
        original = EvalSuite(
            project="X",
            target="anthropic_skill",
            skill_cases=[
                _skill_case(name="a"),
                _skill_case(name="b", tags=["fr"]),
            ],
        )
        restored = EvalSuite.model_validate(original.model_dump())
        assert restored == original

    def test_round_trip_via_json(self) -> None:
        original = EvalSuite(project="X", target="rag", rag_cases=[_rag_case()])
        restored = EvalSuite.model_validate_json(original.model_dump_json())
        assert restored == original
