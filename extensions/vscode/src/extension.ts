/**
 * ContextOS VSCode extension — Phase 7.4.
 *
 * Thin wrapper around the `ctx lsp` language server. The Python side
 * does all the work (parsing, linting, completion, hover, code
 * actions); this extension is just plumbing:
 *
 *   1. Resolve the `ctx` binary (configurable via
 *      `contextos.command`, defaults to whatever resolves on PATH).
 *   2. Spawn it as a stdio LSP server.
 *   3. Register the language client with a document selector
 *      covering `.ctx` files (claimed via the `contextos-ctx`
 *      language ID) and any file named `SKILL.md` (claimed via a
 *      glob pattern so the user's normal Markdown setup stays
 *      authoritative for everything else).
 *
 * A single `ContextOS: Restart language server` command lets the
 * user recycle the client without reloading the whole window.
 */

import * as vscode from 'vscode';
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  client = await startClient(context);

  context.subscriptions.push(
    vscode.commands.registerCommand('contextos.restartServer', async () => {
      if (client) {
        await client.stop();
      }
      client = await startClient(context);
    }),
  );
}

export async function deactivate(): Promise<void> {
  if (client) {
    await client.stop();
    client = undefined;
  }
}

async function startClient(
  _context: vscode.ExtensionContext,
): Promise<LanguageClient> {
  const config = vscode.workspace.getConfiguration('contextos');
  const command = config.get<string>('command', 'ctx');

  // Stdio transport: spawn `ctx lsp` and pipe stdin/stdout.
  // The Python side picks up the LSP framing automatically via pygls.
  const serverOptions: ServerOptions = {
    run: {
      command,
      args: ['lsp'],
      transport: TransportKind.stdio,
    },
    debug: {
      command,
      args: ['lsp'],
      transport: TransportKind.stdio,
    },
  };

  // Document selector: claim `contextos-ctx` (our own language ID for
  // *.ctx) and SKILL.md files. The glob pattern avoids claiming the
  // generic `markdown` language so the user's normal Markdown
  // workflow stays intact on every other .md.
  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: 'file', language: 'contextos-ctx' },
      { scheme: 'file', pattern: '**/SKILL.md' },
    ],
    synchronize: {
      configurationSection: 'contextos',
    },
    outputChannelName: 'ContextOS',
  };

  const newClient = new LanguageClient(
    'contextos',
    'ContextOS',
    serverOptions,
    clientOptions,
  );

  try {
    await newClient.start();
  } catch (err) {
    // The most common failure mode is `ctx` not on PATH or the `lsp`
    // extras not installed. Surface a one-shot notification with the
    // recovery command rather than dropping the error into a hidden
    // output channel.
    void vscode.window.showErrorMessage(
      `Failed to start ContextOS language server. ` +
        `Check that '${command}' is on PATH and was installed with ` +
        `'pipx install context-os[lsp]'. ` +
        `Details: ${err instanceof Error ? err.message : String(err)}`,
    );
    throw err;
  }

  return newClient;
}
