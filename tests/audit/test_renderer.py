"""Tests for the audit renderers."""

from __future__ import annotations

import json
from pathlib import Path

from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Severity
from contextos.ast.document import Document
from contextos.audit import AgentFile, ProjectInferred, audit_project
from contextos.audit.project import SkippedFile
from contextos.audit.renderer import render_audit_cli, render_audit_json


def _agent_file(path: Path, rules: list[Rule]) -> AgentFile:
    return AgentFile(
        path=path,
        target="claude_code",
        document=Document(
            project=path.stem,
            agent=AgentDocument(rules=rules),
        ),
    )


def _rule(rid: str, title: str = "t") -> Rule:
    return Rule(id=rid, title=title, severity=Severity.MUST)


class TestCliRendering:
    def test_empty_repo(self, tmp_path: Path) -> None:
        report = audit_project(ProjectInferred(repo_path=tmp_path))
        out = render_audit_cli(report)
        assert "no recognized agent files found" in out

    def test_per_file_section(self, tmp_path: Path) -> None:
        f = _agent_file(tmp_path / "CLAUDE.md", [_rule("STYLE-001", title="Be concise")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[f]))
        out = render_audit_cli(report)
        assert "--- " in out
        assert "CLAUDE.md" in out
        assert "warning[A001]" in out

    def test_cross_artifact_section_appears_only_with_findings(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", title="A")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", title="B")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        out = render_audit_cli(report)
        assert "Cross-artifact" in out
        assert "XA001" in out

    def test_skipped_files_section(self, tmp_path: Path) -> None:
        f = _agent_file(tmp_path / "CLAUDE.md", [])
        project = ProjectInferred(
            repo_path=tmp_path,
            agent_files=[f],
            skipped_files=[
                SkippedFile(
                    path=tmp_path / ".cursorrules",
                    target="cursor",
                    reason="no parser",
                )
            ],
        )
        report = audit_project(project)
        out = render_audit_cli(report)
        assert "Skipped files" in out
        assert ".cursorrules" in out
        assert "cursor" in out

    def test_summary_line(self, tmp_path: Path) -> None:
        f = _agent_file(tmp_path / "CLAUDE.md", [_rule("X-001", title="Be concise")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[f]))
        out = render_audit_cli(report)
        assert "summary:" in out

    def test_trailing_newline(self, tmp_path: Path) -> None:
        report = audit_project(ProjectInferred(repo_path=tmp_path))
        out = render_audit_cli(report)
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


class TestJsonRendering:
    def test_empty_shape(self, tmp_path: Path) -> None:
        report = audit_project(ProjectInferred(repo_path=tmp_path))
        payload = json.loads(render_audit_json(report))
        assert payload["per_file"] == {}
        assert payload["cross_artifact"] == []
        assert payload["skipped"] == []
        assert payload["total_count"] == 0

    def test_per_file_payload(self, tmp_path: Path) -> None:
        f = _agent_file(tmp_path / "CLAUDE.md", [_rule("X-001", title="Be concise")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[f]))
        payload = json.loads(render_audit_json(report))
        # One file in per_file, with at least one diagnostic.
        assert len(payload["per_file"]) == 1
        first_file_diags = next(iter(payload["per_file"].values()))
        codes = {d["code"] for d in first_file_diags}
        assert "A001" in codes

    def test_cross_artifact_payload(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", title="A")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", title="B")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        payload = json.loads(render_audit_json(report))
        assert any(d["code"] == "XA001" for d in payload["cross_artifact"])

    def test_indent(self, tmp_path: Path) -> None:
        report = audit_project(ProjectInferred(repo_path=tmp_path))
        out = render_audit_json(report, indent=2)
        assert "\n" in out
        assert "  " in out
