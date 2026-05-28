# ContextOS — VSCode extension

LSP-powered tooling for ContextOS `.ctx` and `SKILL.md` files inside
VSCode. Surfaces the same 27 lint rules, completion, hover, and
quick-fix code actions the `ctx` CLI does — just inline as you type.

## Install

The extension drives the Python `ctx lsp` server. Install both:

```bash
pipx install context-os-ctx[lsp]
```

Then install this extension from the VSCode marketplace (or via the
`.vsix` produced by `npm run package`).

## What you get

- **Diagnostics** for every rule in the
  [ContextOS catalog](https://contextos.dev/rules) — A001 vague
  directives, S001 missing trigger phrasing, R001 excessive chunk
  overlap, etc. Each diagnostic carries a `code_description` link
  to its docs page.
- **Completion** on `.ctx` files: top-level keys, section names
  (`[rag]`, `[[skill]]`, `[[document]]`, …), and value enums
  (`severity = "must" | "should" | "may"`, chunking strategies,
  output formats). Plus YAML frontmatter keys on `SKILL.md`.
- **Hover** on any rule code in your file (e.g. `A001`) opens its
  reference docs page.
- **Quick-fix code actions** (lightbulb menu) on every diagnostic
  with a suggestion. The X003 rule (rule titles ending with `?`)
  ships a one-click structured fix that strips the trailing `?`.
- **Restart command**: `ContextOS: Restart language server` from
  the command palette recycles the LSP client without reloading
  the editor.

## Settings

| Key | Default | Description |
| --- | --- | --- |
| `contextos.command` | `ctx` | Path to the `ctx` CLI executable. Set this if `pipx` installs land outside your `PATH` or you want to pin a specific virtualenv. |
| `contextos.trace.server` | `off` | LSP traffic tracing — `messages` for high-level RPC, `verbose` for full payloads. Output goes to the ContextOS output channel. |

## Develop locally

```bash
cd extensions/vscode
npm install
npm run build       # compiles src/extension.ts -> dist/extension.js
# F5 in VSCode to launch the Extension Development Host
```

To produce a `.vsix` for sideloading or marketplace upload:

```bash
npm run package
```

## License

MIT — see the root [LICENSE](../../LICENSE).
