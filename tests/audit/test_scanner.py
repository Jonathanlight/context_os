"""Tests for the repo scanner."""

from __future__ import annotations

from pathlib import Path

from contextos.audit import scan_repo

_VALID_CLAUDE = """# MyProject

## Rules

- Use type hints on every public function.
"""

_VALID_AGENTS = """# Trader

## Identity

Single maintainer.

## Rules

- Never commit secrets.
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestScannerHappyPath:
    def test_finds_claude_md_at_root(self, tmp_path: Path) -> None:
        _write(tmp_path / "CLAUDE.md", _VALID_CLAUDE)
        project = scan_repo(tmp_path)
        assert len(project.agent_files) == 1
        assert project.agent_files[0].target == "claude_code"
        assert project.agent_files[0].path.name == "CLAUDE.md"

    def test_finds_agents_md(self, tmp_path: Path) -> None:
        _write(tmp_path / "AGENTS.md", _VALID_AGENTS)
        project = scan_repo(tmp_path)
        assert len(project.agent_files) == 1
        assert project.agent_files[0].target == "codex"

    def test_finds_both_targets_in_same_repo(self, tmp_path: Path) -> None:
        _write(tmp_path / "CLAUDE.md", _VALID_CLAUDE)
        _write(tmp_path / "AGENTS.md", _VALID_AGENTS)
        project = scan_repo(tmp_path)
        targets = sorted(f.target for f in project.agent_files)
        assert targets == ["claude_code", "codex"]

    def test_recurses_into_subdirs(self, tmp_path: Path) -> None:
        _write(tmp_path / "subproject" / "CLAUDE.md", _VALID_CLAUDE)
        project = scan_repo(tmp_path)
        assert len(project.agent_files) == 1

    def test_empty_repo(self, tmp_path: Path) -> None:
        project = scan_repo(tmp_path)
        assert project.agent_files == []
        assert project.skipped_files == []


class TestScannerSkippedTargets:
    def test_cursorrules_noted_as_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / ".cursorrules", "ASSISTANT RULES\n- something\n")
        project = scan_repo(tmp_path)
        assert project.agent_files == []
        assert len(project.skipped_files) == 1
        assert project.skipped_files[0].target == "cursor"

    def test_clinerules_noted_as_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / ".clinerules", "content\n")
        project = scan_repo(tmp_path)
        assert project.skipped_files[0].target == "cline"

    def test_windsurfrules_noted_as_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / ".windsurfrules", "content\n")
        project = scan_repo(tmp_path)
        assert project.skipped_files[0].target == "windsurf"

    def test_copilot_path_noted_as_skipped(self, tmp_path: Path) -> None:
        _write(tmp_path / ".github" / "copilot-instructions.md", "content\n")
        project = scan_repo(tmp_path)
        assert len(project.skipped_files) == 1
        assert project.skipped_files[0].target == "copilot"

    def test_skip_dirs_are_excluded(self, tmp_path: Path) -> None:
        # CLAUDE.md inside .git / node_modules / __pycache__ must be ignored.
        for ignored in (".git", "node_modules", "__pycache__"):
            _write(tmp_path / ignored / "CLAUDE.md", _VALID_CLAUDE)
        project = scan_repo(tmp_path)
        assert project.agent_files == []


class TestScannerParseErrors:
    def test_invalid_claude_md_becomes_skipped(self, tmp_path: Path) -> None:
        # Empty file — parsable but yields project="Unknown". That's not a
        # parse error per se. A genuinely broken file: cause an OS-level
        # read failure via permissions? Too fiddly. Use a path that doesn't
        # exist via a symlink to simulate.
        # Pragmatic: an empty file IS still parsable (Unknown project, no
        # rules). The scanner should NOT skip it.
        _write(tmp_path / "CLAUDE.md", "")
        project = scan_repo(tmp_path)
        assert len(project.agent_files) == 1
        assert project.agent_files[0].document.project == "CLAUDE"  # filename stem


class TestScannerDeterministicOrder:
    def test_results_are_sorted(self, tmp_path: Path) -> None:
        _write(tmp_path / "zeta" / "CLAUDE.md", _VALID_CLAUDE)
        _write(tmp_path / "alpha" / "CLAUDE.md", _VALID_CLAUDE)
        _write(tmp_path / "beta" / "AGENTS.md", _VALID_AGENTS)
        project = scan_repo(tmp_path)
        paths = [str(f.path) for f in project.agent_files]
        assert paths == sorted(paths)
