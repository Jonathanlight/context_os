"""Filesystem walker — finds every recognized agent file under a root."""

from __future__ import annotations

from pathlib import Path

from contextos.audit.project import AgentFile, ProjectInferred, SkippedFile
from contextos.parsers import ContextOSParseError, parse_markdown_file

# Map basename (relative to repo root) -> (target name, parser available)
# `.github/copilot-instructions.md` is matched by suffix because the
# `.github/` prefix is a path segment, not a basename.
_PARSEABLE_BASENAMES: dict[str, str] = {
    "CLAUDE.md": "claude_code",
    "AGENTS.md": "codex",
}
_SKIPPED_BASENAMES: dict[str, str] = {
    ".cursorrules": "cursor",
    ".clinerules": "cline",
    ".windsurfrules": "windsurf",
}
_SKIPPED_RELATIVE_PATHS: dict[str, str] = {
    ".github/copilot-instructions.md": "copilot",
}

# Directories the scanner never descends into. Keeping the list small
# avoids fighting users' build / VCS conventions — the burden is on the
# user to use `--exclude` (future) for project-specific opt-outs.
_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"})


def scan_repo(root: Path) -> ProjectInferred:
    """Walk ``root`` recursively and parse every recognized agent file."""
    root = root.resolve()
    agent_files: list[AgentFile] = []
    skipped_files: list[SkippedFile] = []

    for path in _walk(root):
        rel = path.relative_to(root)
        rel_posix = rel.as_posix()
        target = _PARSEABLE_BASENAMES.get(path.name)
        if target is not None:
            entry = _parse_agent(path, target=target)
            if isinstance(entry, AgentFile):
                agent_files.append(entry)
            else:
                skipped_files.append(entry)
            continue

        target = _SKIPPED_BASENAMES.get(path.name) or _SKIPPED_RELATIVE_PATHS.get(rel_posix)
        if target is not None:
            skipped_files.append(
                SkippedFile(
                    path=path,
                    target=target,
                    reason=f"no parser yet for target '{target}'",
                )
            )

    return ProjectInferred(
        repo_path=root,
        agent_files=agent_files,
        skipped_files=skipped_files,
    )


def _walk(root: Path) -> list[Path]:
    """Depth-first walk, skipping :data:`_SKIP_DIRS`. Returns a sorted list
    so two scans of the same tree produce the same audit ordering.
    """
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        found.append(path)
    return found


def _parse_agent(path: Path, *, target: str) -> AgentFile | SkippedFile:
    """Attempt to parse one agent file; degrade gracefully on parse error."""
    try:
        doc = parse_markdown_file(path, target=target)
    except ContextOSParseError as exc:
        return SkippedFile(path=path, target=target, reason=f"parse error: {exc}")
    return AgentFile(path=path, target=target, document=doc)
