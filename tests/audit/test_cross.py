"""Tests for the cross-artifact audit (XA001) and the audit_project orchestrator."""

from __future__ import annotations

from pathlib import Path

from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Severity
from contextos.ast.document import Document
from contextos.audit import AgentFile, ProjectInferred, audit_project
from contextos.audit.project import SkippedFile


def _agent_file(path: Path, rules: list[Rule]) -> AgentFile:
    return AgentFile(
        path=path,
        target="claude_code",
        document=Document(
            project=path.stem,
            agent=AgentDocument(rules=rules),
        ),
    )


def _rule(rid: str, title: str = "t", severity: Severity = Severity.MUST) -> Rule:
    return Rule(id=rid, title=title, severity=severity)


class TestXA001Detection:
    def test_same_id_different_content_fires(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", title="Tests first")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", title="Different title")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        codes = [d.code for d in report.cross_artifact]
        assert "XA001" in codes

    def test_same_id_same_content_does_not_fire(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        assert all(d.code != "XA001" for d in report.cross_artifact)

    def test_single_file_does_not_fire(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a]))
        assert report.cross_artifact == []

    def test_different_severity_counts_as_collision(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", severity=Severity.MUST)])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", severity=Severity.SHOULD)])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        assert any(d.code == "XA001" for d in report.cross_artifact)

    def test_message_lists_all_colliding_files(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", title="A")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", title="B")])
        c = _agent_file(tmp_path / "c/CLAUDE.md", [_rule("TDD-001", title="C")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b, c]))
        xa = next(d for d in report.cross_artifact if d.code == "XA001")
        # Three files mentioned in the message.
        assert "a/CLAUDE.md" in xa.message
        assert "b/CLAUDE.md" in xa.message
        assert "c/CLAUDE.md" in xa.message


class TestPerFileAnalyzers:
    def test_per_file_diagnostics_run(self, tmp_path: Path) -> None:
        # A "Be concise" rule fires A001 + K002 + K003 (no rationale / examples).
        f = _agent_file(
            tmp_path / "CLAUDE.md",
            [_rule("STYLE-001", title="Be concise")],
        )
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[f]))
        diags = report.per_file[str(f.path)]
        codes = {d.code for d in diags}
        assert "A001" in codes  # vague directive
        assert "K002" in codes  # no rationale on must-rule
        assert "K003" in codes  # no examples on must-rule

    def test_empty_project_yields_empty_report(self, tmp_path: Path) -> None:
        report = audit_project(ProjectInferred(repo_path=tmp_path))
        assert report.per_file == {}
        assert report.cross_artifact == []
        assert report.total_count() == 0


class TestAuditReport:
    def test_total_count(self, tmp_path: Path) -> None:
        a = _agent_file(tmp_path / "a/CLAUDE.md", [_rule("TDD-001", title="Be concise")])
        b = _agent_file(tmp_path / "b/CLAUDE.md", [_rule("TDD-001", title="Other")])
        report = audit_project(ProjectInferred(repo_path=tmp_path, agent_files=[a, b]))
        # A001+K002+K003 per file (2*3=6) + 1 XA001 cross = 7.
        assert report.total_count() >= 5

    def test_skipped_files_propagate(self, tmp_path: Path) -> None:
        project = ProjectInferred(
            repo_path=tmp_path,
            skipped_files=[
                SkippedFile(
                    path=tmp_path / ".cursorrules",
                    target="cursor",
                    reason="no parser yet",
                )
            ],
        )
        report = audit_project(project)
        assert len(report.skipped) == 1
        assert report.skipped[0]["target"] == "cursor"
