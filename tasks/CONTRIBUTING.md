# Contributing to ContextOS

ContextOS enforces strict PR discipline. Read this before opening a pull
request. The rules are tight on purpose — they keep reviews fast and history
readable while we ramp from zero to v1.0.

## Branching

- `develop` is the integration branch. Open PRs against it.
- `main` is reserved for release tags (created in PR `phase1(release): v0.1.0`).
- Feature branches: `feature/phase<N>-<milestone>-<slug>`
  - e.g. `feature/phase1-1.1-ast-models`
- Chore branches (no phase): `chore/<slug>`
  - e.g. `chore/gitignore-cleanup`
- Hotfix branches (post-release only): `hotfix/<slug>`

One branch per task. Delete the branch after merge.

## PR size

**≤ 400 lines diff excluding tests.** Hard cap.

If a milestone naturally produces more, split it:
- `phase1(parsers): klar TOML parser core` (~250 lines)
- `phase1(parsers): klar parser errors + fixtures` (~200 lines)

Pure documentation PRs may exceed 400 lines if the content is cohesive (e.g.
all of `docs/specs/SPEC.md` in one shot), but flag it in the PR description.

## PR title

Use the same format as the squash commit:

```
<phase>(<module>): <short imperative>
```

Examples:
- `phase1(ast): pydantic v2 models for ContextOS AST`
- `phase2(analyzers): implement A001 vague-directive detection`
- `chore(repo): correct .gitignore patterns`

## PR description template

Every PR description must contain these four sections:

```markdown
## Contexte

Why this PR exists. 1–2 sentences. Link the milestone in
`docs/specs/ROADMAP.md` if applicable.

## Changement

Table of files touched and their role. Or bullet list for small PRs.

## Tests

What was covered. Output of `pytest`. CI status.

## DoD

Checklist from the relevant milestone in `tasks/phase<N>_todo.md`.
All boxes checked.
```

Optional sections: **Risks**, **Suite** (what lands next), **Refs**.

## Commit conventions

```
<phase>(<module>): <short imperative>

<optional body, wrapped at 72 cols, the why not the what>

<optional footer: Refs #issue>
```

Examples:
- `phase1(parser): support TOML nested arrays in rules`
- `phase2(analyzers): implement A001 vague-directive detection`
- `phase3(emitters): cursor mdc frontmatter generation`

Body should explain **why**, not **what** (the diff shows the what).

## Merge strategy

**Squash merge.** Every PR becomes one commit on `develop`. The squash commit
adopts the PR title.

Intermediate commits on a feature branch are free-form — write what you need
to keep yourself organized. They are erased at squash time.

## Quality gates (must pass before review request)

```bash
./scripts/check.sh
```

Runs:
1. `ruff check src tests`
2. `ruff format --check src tests`
3. `mypy --strict src tests`
4. `pytest --cov-fail-under=85`

CI runs the same four. A red CI blocks merge. Do not skip hooks
(`--no-verify`).

## One subject per PR

Forbidden combinations in a single PR:
- New feature + refactor of unrelated code
- Bug fix + dependency bump
- Code change + spec change

If you find yourself wanting to do two things, open two PRs. Stack them with
chained branches if there is a dependency:

```
develop
  └─ feature/phase1-1.1-ast-models   (PR #5)
       └─ feature/phase1-1.2-klar-parser (PR #6, depends on #5)
```

Rebase the dependent branch onto `develop` after the parent merges.

## What requires an asked human approval

See `CLAUDE.md → When to ask the human`. Summary:

You **must** ask before:
- Adding a Python dependency
- Modifying `docs/specs/SPEC.md`
- Architectural choice not in `docs/specs/ARCHITECTURE.md`
- New lint rule code
- New emitter output format

## Co-authorship

If a PR was produced in collaboration with an AI assistant (Claude Code,
Cursor, Copilot), credit it in the commit trailer:

```
Co-authored-by: Claude <noreply@anthropic.com>
```

## Releases

Release PRs follow the format `phase<N>(release): v<X.Y.Z>` and bump:
- `pyproject.toml` version
- `CHANGELOG.md`
- Git tag `v<X.Y.Z>` after merge to `main`

See `tasks/phase<N>_todo.md` for the active release milestone.
