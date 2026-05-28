# Editor integration

Phase 7A wires ContextOS into the tools where context files are
actually authored. The same 27 lint rules, completion, hover, and
quick-fix code actions that drive `ctx lint` / `ctx audit` are
available **inline** through the Language Server Protocol.

## Architecture

```
┌────────────────┐     LSP/stdio      ┌─────────────────┐
│  VSCode (or    │ ◄─────────────────► │  ctx lsp        │
│  Neovim / Helix│                     │  (Python, pygls)│
│  / Sublime /…) │                     │                 │
└────────────────┘                     │  Reuses:        │
                                       │  - ctx_parser   │
                                       │  - lint_document│
                                       │  - all analyzers│
                                       └─────────────────┘
```

The editor speaks LSP over stdio to a Python subprocess (`ctx lsp`).
The server is the same Python package as the CLI — there is **no
parallel implementation** that could drift. A diagnostic that fires
in `ctx audit` fires in the editor too, with the same code, the same
message, and the same suggested fix.

## Install

The LSP server ships as an optional extras group so CLI-only users
don't pay for `pygls`.

> **PyPI publication is pending** — install from the git source until
> the first release lands.

```bash
# From git source (today)
pipx install 'git+https://github.com/Jonathanlight/context_os.git#egg=context-os-ctx[lsp]'

# Once published on PyPI
pipx install 'context-os-ctx[lsp]'
# or
pip install 'context-os-ctx[lsp]'
```

Verify the binary spawns:

```bash
ctx lsp < /dev/null
# (immediately exits cleanly — the server expects LSP framing on stdin)
```

## VSCode

The official extension lives at
[`extensions/vscode/`](https://github.com/Jonathanlight/context_os/tree/develop/extensions/vscode)
in the ContextOS repo. Install it via the Marketplace (once published)
or sideload the `.vsix`:

```bash
cd extensions/vscode
npm ci
npm run build
npm run package
code --install-extension contextos-2.1.0.vsix
```

### Settings

| Setting | Default | Description |
| --- | --- | --- |
| `contextos.command` | `ctx` | Path to the `ctx` executable. Pin a virtualenv with an absolute path when `pipx` lands outside `PATH`. |
| `contextos.trace.server` | `off` | LSP traffic tracing. `messages` for RPC summaries; `verbose` for full payloads. Output lands in the **ContextOS** output channel. |

### Commands

- **`ContextOS: Restart language server`** — recycle the LSP client without reloading the window. Useful after editing `pyproject.toml` or switching virtualenvs.

## Neovim (lspconfig)

ContextOS isn't in `nvim-lspconfig`'s registry yet, but the manual
setup is trivial:

```lua
local lspconfig_util = require('lspconfig.util')
local configs = require('lspconfig.configs')

if not configs.contextos then
  configs.contextos = {
    default_config = {
      cmd = { 'ctx', 'lsp' },
      filetypes = { 'toml', 'markdown' },
      root_dir = lspconfig_util.root_pattern('*.ctx', 'SKILL.md', '.git'),
      single_file_support = true,
    },
  }
end

require('lspconfig').contextos.setup{}
```

## Helix

Add to `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "toml"
language-servers = ["taplo", "contextos"]

[language-server.contextos]
command = "ctx"
args = ["lsp"]
```

The Helix `toml` language already handles syntax highlighting; the
`contextos` server adds the lint layer on top.

## Sublime Text (LSP package)

`~/.config/sublime-text/Packages/User/LSP.sublime-settings`:

```json
{
  "clients": {
    "contextos": {
      "enabled": true,
      "command": ["ctx", "lsp"],
      "selector": "source.toml | text.html.markdown"
    }
  }
}
```

## What you get

- **Diagnostics** for every rule in the
  [rules catalog](rules/index.md) — A001 vague directives, S001
  missing trigger phrasing, R001 excessive chunk overlap, etc.
  Each diagnostic carries a `code_description` link to its docs
  page so the editor can render a clickable rule reference.
- **Completion** on `.ctx` files: top-level keys, section names
  (`[rag]`, `[[skill]]`, `[[document]]`, …), and value enums
  (`severity = "must" | "should" | "may"`, chunking strategies,
  output formats). Plus YAML frontmatter keys on `SKILL.md`.
- **Hover** on any rule code in your file (e.g. `A001`) opens a
  Markdown blob linking to its reference docs page.
- **Quick-fix code actions** (lightbulb menu) on every diagnostic
  with a suggestion. Phase 7.3 ships one structured fix
  (X003 — strip the trailing `?`); follow-up PRs extend the
  structured-fix table.

## GitHub Action

For CI rather than IDE, the
[`contextos/lint-action`](https://github.com/Jonathanlight/context_os/tree/develop/actions/lint)
composite Action surfaces the same diagnostics inline in the
workflow log and as a sticky PR comment:

```yaml
name: ContextOS lint
on: [pull_request, push]

permissions:
  contents: read
  pull-requests: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Jonathanlight/context_os/actions/lint@v2.1.0
```

See [`actions/lint/README.md`](https://github.com/Jonathanlight/context_os/tree/develop/actions/lint)
for the full input table and the sticky-comment behavior.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ctx lsp` not found | Installed without `[lsp]` extras | `pipx install --force context-os-ctx[lsp]` |
| VSCode shows a one-shot error notification at activation | `contextos.command` points at a missing binary | Set the absolute path in settings |
| No diagnostics on `SKILL.md` | The extension watches `**/SKILL.md`; case-sensitive | Confirm the filename is exactly `SKILL.md` |
| LSP traffic dump empty | `contextos.trace.server` is `off` | Bump to `messages` and reload |
