const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function getRepoRoot() {
  const cfg = vscode.workspace.getConfiguration("termorganism");
  const configured = cfg.get("repoRoot");
  if (configured && configured.trim()) return configured;
  const ws = vscode.workspace.workspaceFolders;
  if (ws && ws.length) return ws[0].uri.fsPath;
  return "";
}

function binPath(name) {
  const root = getRepoRoot();
  return root ? path.join(root, "bin", name) : "";
}

function runJson(bin, args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(bin, args, { stdio: ["pipe", "pipe", "pipe"] });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => out += d.toString());
    child.stderr.on("data", (d) => err += d.toString());
    child.on("error", reject);
    child.on("close", (code) => {
      if (!out.trim()) {
        return resolve({ code, data: null, stderr: err });
      }
      try {
        resolve({ code, data: JSON.parse(out), stderr: err });
      } catch (e) {
        reject(new Error(`JSON parse failed: ${e.message}\nSTDOUT=${out}\nSTDERR=${err}`));
      }
    });
    if (input != null) child.stdin.end(input);
    else child.stdin.end();
  });
}

class WhisperItem extends vscode.TreeItem {
  constructor(label, description, tooltip) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = description;
    this.tooltip = tooltip;
  }
}

class WhisperProvider {
  constructor() {
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    this.items = [new WhisperItem("No active file", "", "")];
  }

  refresh() { this._onDidChangeTreeData.fire(); }
  getTreeItem(item) { return item; }
  getChildren() { return this.items; }

  async updateFromActiveEditor() {
    const editor = vscode.window.activeTextEditor;
    const sidebarBin = binPath("termorganism-sidebar");
    if (!editor || !sidebarBin || !fs.existsSync(sidebarBin)) {
      this.items = [new WhisperItem("TermOrganism unavailable", "check repoRoot/bin", "TermOrganism sidebar binary not found")];
      this.refresh();
      return;
    }

    const file = editor.document.uri.fsPath;
    try {
      const res = await runJson(sidebarBin, [file, "--once"], null);
      const payload = res.data || {};
      const diagnostics = payload.diagnostics || [];
      const top = payload.top_whisper || "quiet";
      const items = [new WhisperItem(top, `${payload.count || 0} diagnostics`, top)];
      for (const d of diagnostics.slice(0, 8)) {
        items.push(new WhisperItem(d.kind, `p=${d.priority}`, d.message));
      }
      this.items = items;
    } catch (e) {
      this.items = [new WhisperItem("Sidebar error", "", String(e.message || e))];
    }
    this.refresh();
  }
}

async function runPreSaveCheck(document) {
  const bin = binPath("termorganism-pre-save");
  if (!bin || !fs.existsSync(bin)) return;

  try {
    const input = document.getText();
    const res = await runJson(bin, [document.uri.fsPath, "--stdin", "--json", "--block-on-error"], input);
    const payload = res.data || {};
    if (payload.has_error) {
      const block = vscode.workspace.getConfiguration("termorganism").get("preSave.blockOnError");
      const msg = `TermOrganism: save risk detected — ${payload.top_whisper || "error"}`;
      if (block) vscode.window.showErrorMessage(msg);
      else vscode.window.showWarningMessage(msg);
    } else if (payload.has_warning) {
      vscode.window.setStatusBarMessage(`TermOrganism: ${payload.top_whisper}`, 3000);
    }
  } catch (e) {
    vscode.window.setStatusBarMessage(`TermOrganism pre-save error: ${e.message}`, 4000);
  }
}

async function previewFixesForUri(uri) {
  const file = uri ? vscode.Uri.parse(uri).fsPath : (vscode.window.activeTextEditor?.document.uri.fsPath || "");
  if (!file) return;

  const bin = binPath("termorganism-fix-preview");
  if (!bin || !fs.existsSync(bin)) {
    vscode.window.showErrorMessage("termorganism-fix-preview binary bulunamadı");
    return;
  }

  try {
    const res = await runJson(bin, [file, "--json"], null);
    const payload = res.data || {};
    const actions = payload.actions || [];
    if (!actions.length) {
      vscode.window.showInformationMessage("TermOrganism: preview fix bulunamadı");
      return;
    }

    const picked = await vscode.window.showQuickPick(
      actions.map(a => ({
        label: a.title,
        description: a.diagnostic_kind,
        detail: a.message,
        action: a,
      })),
      { placeHolder: "TermOrganism fix preview seç" }
    );

    if (!picked) return;

    const doc = await vscode.workspace.openTextDocument({
      content: `${picked.action.title}\n\n${picked.action.preview || picked.action.message}`,
      language: "markdown"
    });
    await vscode.window.showTextDocument(doc, { preview: true });
  } catch (e) {
    vscode.window.showErrorMessage(`TermOrganism preview error: ${e.message}`);
  }
}

async function activate(context) {
  const root = getRepoRoot();
  if (!root) vscode.window.showWarningMessage("TermOrganism: repoRoot bulunamadı");

  const lspBin = binPath("termorganism-lsp");
  if (lspBin && fs.existsSync(lspBin)) {
    const serverOptions = { command: lspBin, transport: TransportKind.stdio };
    const clientOptions = { documentSelector: [{ scheme: "file", language: "python" }] };
    client = new LanguageClient("termorganism-lsp", "TermOrganism LSP", serverOptions, clientOptions);
    context.subscriptions.push(client.start());
  } else {
    vscode.window.showWarningMessage("TermOrganism LSP binary bulunamadı");
  }

  const provider = new WhisperProvider();
  vscode.window.registerTreeDataProvider("termorganismWhispers", provider);

  context.subscriptions.push(
    vscode.commands.registerCommand("termorganism.refreshWhispers", async () => {
      await provider.updateFromActiveEditor();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("termorganism.runPreSaveCheck", async () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) await runPreSaveCheck(editor.document);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("termorganism.previewFixes", async (uri) => {
      await previewFixesForUri(uri);
    })
  );

  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(async () => {
    await provider.updateFromActiveEditor();
  }));

  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument(async (e) => {
    const editor = vscode.window.activeTextEditor;
    if (editor && e.document === editor.document) {
      await provider.updateFromActiveEditor();
    }
  }));

  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (doc) => {
    await provider.updateFromActiveEditor();
    await runPreSaveCheck(doc);
  }));

  const editor = vscode.window.activeTextEditor;
  if (editor) await provider.updateFromActiveEditor();
}

async function deactivate() {
  if (client) await client.stop();
}

module.exports = { activate, deactivate };
