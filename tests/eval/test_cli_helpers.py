"""Tests for the ctx eval CLI helpers — Phase 7.10."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contextos.ast.eval import EvalSuite, RagCase, SkillCase
from contextos.eval.cli_helpers import (
    build_dry_run_rag_provider,
    build_dry_run_skill_provider,
    load_chunks,
    load_skills_from_dir,
)


class TestLoadSkillsFromDir:
    def test_walks_recursively(self, tmp_path: Path) -> None:
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "SKILL.md").write_text(
            "---\nname: a\ntitle: A\ndescription: Triggers when the user asks for A.\n---\n\n# A\n",
            encoding="utf-8",
        )
        (tmp_path / "b" / "deep").mkdir(parents=True)
        (tmp_path / "b" / "deep" / "SKILL.md").write_text(
            "---\nname: b\ntitle: B\ndescription: Triggers when the user asks for B.\n---\n\n# B\n",
            encoding="utf-8",
        )
        skills = load_skills_from_dir(tmp_path)
        slugs = sorted(s.name for s in skills)
        assert slugs == ["a", "b"]

    def test_sorted_order_for_determinism(self, tmp_path: Path) -> None:
        for letter in ["c", "a", "b"]:
            d = tmp_path / letter
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {letter}\ntitle: {letter.upper()}\n"
                f"description: Triggers when the user asks for {letter}.\n"
                "---\n",
                encoding="utf-8",
            )
        skills = load_skills_from_dir(tmp_path)
        assert [s.name for s in skills] == ["a", "b", "c"]

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        assert load_skills_from_dir(tmp_path) == []


class TestLoadChunks:
    def test_valid_chunks_file(self, tmp_path: Path) -> None:
        path = tmp_path / "chunks.json"
        path.write_text(
            json.dumps(
                [
                    {"source": "a.md", "vector": [0.1, 0.2]},
                    {"source": "b.md", "vector": [0.3, 0.4], "content": "..."},
                ]
            ),
            encoding="utf-8",
        )
        chunks = load_chunks(path)
        assert len(chunks) == 2
        assert chunks[0].source == "a.md"
        assert chunks[1].content == "..."

    def test_non_list_root_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "chunks.json"
        path.write_text('{"not": "an array"}', encoding="utf-8")
        with pytest.raises(ValueError, match=r"must be a JSON array"):
            load_chunks(path)

    def test_malformed_entry_propagates_validation_error(self, tmp_path: Path) -> None:
        path = tmp_path / "chunks.json"
        path.write_text(
            json.dumps([{"source": "x.md"}]),  # missing vector
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_chunks(path)


class TestDryRunProviders:
    def test_skill_dry_run_passes_every_case(self) -> None:
        suite = EvalSuite(
            project="Test",
            target="anthropic_skill",
            skill_cases=[
                SkillCase(name="a", prompt="P1", expected_skill="skill-a"),
                SkillCase(name="b", prompt="P2", expected_skill="skill-b"),
            ],
        )
        provider = build_dry_run_skill_provider(suite)
        # Every case prompt returns its own expected_skill.
        for case in suite.skill_cases:
            response = provider.route(case.prompt, skills=[])
            assert response.picked_skill == case.expected_skill

    def test_rag_dry_run_returns_expected_sources(self) -> None:
        suite = EvalSuite(
            project="Test",
            target="rag",
            rag_cases=[
                RagCase(name="a", query="Q1", expected_sources=["docs/a.md"]),
                RagCase(
                    name="b",
                    query="Q2",
                    expected_sources=["docs/b.md", "docs/c.md"],
                ),
            ],
        )
        provider = build_dry_run_rag_provider(suite)
        response_a = provider.retrieve("Q1", top_k=5)
        assert response_a.retrieved_sources == ["docs/a.md"]
        response_b = provider.retrieve("Q2", top_k=5)
        assert response_b.retrieved_sources == ["docs/b.md", "docs/c.md"]
