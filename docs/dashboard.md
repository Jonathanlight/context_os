# Visualization & auto-fix

Phase 8 turns ContextOS's text-mode output into shippable artifacts:
self-contained HTML reports for audit and eval runs, plus a `ctx fix`
command that auto-applies the structured fixes the linter already
knows about.

## HTML audit report

`ctx audit --html` renders a one-file HTML page with severity
filters, per-file sections, cross-artifact rules, and the skipped-
files list. No external assets — drop it on a static host, attach it
to a PR comment via a `<details>` block, or open it locally.

```bash
ctx audit . --html --output report.html
open report.html
```

The page is intentionally minimal:

- Header with the repo path + three severity filter buttons (counts
  embedded in the button labels).
- Per-file accordion sections, sorted by path; each diagnostic row
  carries severity / code (with doc-link when the rule has one) /
  position / message (with the suggestion inlined as a muted
  quote below).
- Cross-artifact and skipped sections render only when non-empty.
- Footer summary line with the total diagnostic count.

Click any of the **All / Error / Warning / Info** chips at the top
to filter rows in place — the script is 12 lines of vanilla JS, no
framework.

## HTML eval report

`ctx eval --html` does the same for evaluation runs:

```bash
ctx eval skills.eval.toml --dry-run --html --output eval.html
```

The page puts the pass-rate front and center: a large `75%` number
next to a progress-bar fill + `3/4 passing` label, with token total
as a badge. Cases render as a filterable table with `PASS` / `FAIL`
chips; failing cases inline an expected/actual/error block under
the case name.

Use this when you want to share a result with someone who doesn't
want to grep JSON, or to archive a snapshot of a run as a build
artifact.

## `ctx fix` — apply structured fixes

`ctx fix <path>` runs the lint pipeline and applies the structured
fixes the four supported rules ship today:

| Code | What it does |
| --- | --- |
| **X003** | strips a trailing `?` from a rule title |
| **F001** | sentence-cases an ALL CAPS title |
| **X001** | strips `TODO` / `FIXME` / `XXX` / `HACK` markers at the start of a title |
| **S005** | prepends `# <title>` to a SKILL.md body that lacks an H1 |

Default behavior is **dry-run** — the command prints a unified diff
and leaves files untouched:

```bash
$ ctx fix CLAUDE.md
--- CLAUDE.md (X003)
--- CLAUDE.md
+++ CLAUDE.md (fixed)
@@ -3,3 +3,3 @@
 [[rules]]
 id = "X-001"
-title = "Why log everything?"
+title = "Why log everything"
 severity = "should"

dry-run: 1 file(s) would change. Re-run with --apply.
```

Pass `--apply` to write the new content:

```bash
ctx fix CLAUDE.md --apply
```

A directory target walks the tree via the same scanner `ctx audit`
uses, so the set of fixed files matches what `ctx audit` would lint.

### Safety properties

- **Dry-run by default** — same model as `git rebase` and `sed -i`.
  No accidental writes.
- **Idempotent** — applying a fix and re-running it on the result
  produces the same output. The runner re-lints after each pass; a
  fix that doesn't fire just leaves the diagnostic for a human.
- **Conservative** — each fix returns `None` (no edit) when in
  doubt. `X001` only strips a marker at the **start** of a title;
  a title containing `Review TODO list` mid-sentence is left alone.
  `F001` does sentence case — not title case — so acronyms aren't
  damaged.
- **No multi-edit fixes today** — each diagnostic gets at most one
  `TextEdit`. Multi-step refactors (e.g. moving a URL out of a
  title into `links`) need additional plumbing.

### CI integration

Wire `ctx fix --apply` into a pre-commit hook to keep titles
clean on the way in:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: contextos-fix
        name: contextos auto-fix
        entry: ctx fix --apply
        language: system
        files: '(CLAUDE\.md|AGENTS\.md|SKILL\.md|\.ctx)$'
```

Or as a separate GitHub Action step that gates the PR:

```yaml
- run: ctx fix .
  # exits 0 in dry-run mode; the diff lands in the workflow log
- run: git diff --exit-code
  # exit 1 if any file would change → committer should run --apply locally
```

## Roadmap

Visualization and auto-fix land in **v4.0.0**. The deferred items
from earlier phases remain on the Phase 9+ list:

- Multi-provider Skills (OpenAI tools, local models).
- Embedding-provider CLI helpers (Voyage / Cohere shortcuts).
- PDF support in RAG.
- Cursor commands, GPT custom instructions.
- Web app on `contextos.dev/app`.
- LSP definition / documentSymbol for jump-to-rule.
- Additional structured fixes (C001 contradiction rephrase, more
  multi-edit refactors).
