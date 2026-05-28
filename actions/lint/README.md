# `contextos/lint-action`

GitHub Action that runs `ctx audit` on a repository and surfaces the
results both **inline in the workflow log** (rustc-style diagnostics
identical to the CLI) and **as a sticky pull-request comment** that's
updated in place on every re-run.

Composite action — no Docker, no JavaScript runtime; just
`setup-python` + `pip install context-os-ctx` + `ctx audit --json` +
GitHub's REST API for the comment.

## Quick start

```yaml
name: Lint context files
on: [pull_request, push]

jobs:
  contextos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Jonathanlight/context_os/actions/lint@v2.0.0
```

That's it. On every PR you get:

- The audit output in the workflow log (`ctx audit .` raw output).
- A sticky PR comment with per-file diagnostics, cross-artifact rules
  (`XA001` collisions), and the list of files the scanner skipped.

## Inputs

| Name | Default | Description |
| --- | --- | --- |
| `path` | `.` | Path to audit (passed straight to `ctx audit`). |
| `python-version` | `3.12` | Python version for `setup-python`. Must be `>= 3.12`. |
| `context-os-spec` | `context-os-ctx` | pip install spec. Use `context-os-ctx==2.0.0` to pin, `-e ./` for editable installs, or a git URL for unreleased branches. |
| `fail-on-error` | `true` | Exit non-zero when the audit reports any **error-severity** diagnostic. Warnings and info never affect the exit code. |
| `comment-on-pr` | `true` | Post a sticky PR comment with the report. Honored only on `pull_request` events. |
| `github-token` | `${{ github.token }}` | Override only if you need cross-repo comment posting. |

## Outputs

| Name | Description |
| --- | --- |
| `exit-code` | Exit code from `ctx audit`. 0 = clean (no error-severity), 1 = errors fired. |
| `diagnostic-count` | Total number of diagnostics across all files + cross-artifact + skipped. |
| `audit-json-path` | Filesystem path to the raw JSON report (`audit.json` in the workflow workspace). Useful for follow-up steps. |

## Examples

### Pin to a specific ContextOS version

```yaml
- uses: Jonathanlight/context_os/actions/lint@v2.0.0
  with:
    context-os-spec: 'context-os-ctx==2.0.0'
```

### Audit a subdirectory only

```yaml
- uses: Jonathanlight/context_os/actions/lint@v2.0.0
  with:
    path: 'agents/'
```

### Surface diagnostics but never fail the workflow

```yaml
- uses: Jonathanlight/context_os/actions/lint@v2.0.0
  with:
    fail-on-error: 'false'
```

### Consume the JSON in a follow-up step

```yaml
- id: lint
  uses: Jonathanlight/context_os/actions/lint@v2.0.0
  with:
    fail-on-error: 'false'

- name: Custom post-processing
  if: always()
  run: |
    cat "${{ steps.lint.outputs.audit-json-path }}" | jq '.per_file'
    echo "Total diagnostics: ${{ steps.lint.outputs.diagnostic-count }}"
```

## How the PR comment behaves

- **First run on a PR** — new comment posted, tagged with a hidden
  HTML marker (`<!-- contextos-lint-action-comment -->`).
- **Re-runs of the same PR** — the existing comment is found by the
  marker and **updated in place**. You never see two ContextOS
  comments on the same PR.
- **Pushes to a branch (not a PR)** — the action runs but does not
  post; results stay in the workflow log.

## Required permissions

The default `GITHUB_TOKEN` works in same-repo workflows. For
fork-originated PRs, GitHub passes a read-only token; the comment
step silently fails. The workflow-level setting that fixes this:

```yaml
permissions:
  pull-requests: write
```

## Versioning

This action ships from the same repository as ContextOS itself. The
tag refs follow the package's semantic version (`v2.0.0`, `v2.1.0`, …),
so pinning to a major (`@v2`) is the recommended pattern once
v2 → v3 happens.

## License

MIT — see the root [LICENSE](../../LICENSE).
