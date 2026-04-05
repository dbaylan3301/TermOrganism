from __future__ import annotations

import json
import sys
from typing import Any

from core.watch.predictive_runtime import analyze_python_text
from core.editor.code_actions import build_code_actions_for_text


class LSPServer:
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.shutdown_requested = False

    def _send(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()

    def _read(self) -> dict[str, Any] | None:
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            if line == b"\r\n":
                break
            key, value = line.decode("utf-8", "ignore").split(":", 1)
            headers[key.strip().lower()] = value.strip()

        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = sys.stdin.buffer.read(length)
        if not body:
            return None
        return json.loads(body.decode("utf-8", "ignore"))

    def _uri_to_path(self, uri: str) -> str:
        if uri.startswith("file://"):
            return uri[7:]
        return uri

    def _publish_diagnostics(self, uri: str, text: str) -> None:
        path = self._uri_to_path(uri)
        payload = analyze_python_text(text, file_path=path)
        diagnostics = []
        severity_map = {"error": 1, "warning": 2, "info": 3, "hint": 4}
        for d in payload.get("diagnostics", []):
            diagnostics.append({
                "range": {
                    "start": {"line": max(0, int(d["line"]) - 1), "character": int(d["column"])},
                    "end": {"line": max(0, int(d["end_line"]) - 1), "character": int(d["end_column"])},
                },
                "severity": severity_map.get(str(d.get("severity", "warning")), 2),
                "code": d.get("code", d.get("kind", "termorganism")),
                "source": "termorganism",
                "message": f"{d['kind']}: {d['message']} | priority={d['priority']}",
            })

        self._send({
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": diagnostics,
            },
        })

    def _code_actions(self, uri: str) -> list[dict[str, Any]]:
        text = self.documents.get(uri, "")
        path = self._uri_to_path(uri)
        payload = build_code_actions_for_text(text, file_path=path)
        actions = []

        # direct edit quickfixes
        for item in payload.get("actions", []):
            if item.get("auto_apply") and (item.get("edit") or item.get("edits")):
                raw_edits = item.get("edits") or ([item["edit"]] if item.get("edit") else [])
                lsp_edits = []
                for e in raw_edits:
                    lsp_edits.append({
                        "range": {
                            "start": {"line": max(0, int(e["start_line"]) - 1), "character": int(e["start_col"])},
                            "end": {"line": max(0, int(e["end_line"]) - 1), "character": int(e["end_col"])},
                        },
                        "newText": e["new_text"],
                    })

                actions.append({
                    "title": item["title"],
                    "kind": "quickfix",
                    "edit": {
                        "changes": {
                            uri: lsp_edits
                        }
                    }
                })

        # preview action
        if payload.get("actions"):
            actions.append({
                "title": "TermOrganism: Preview suggestions",
                "kind": "refactor.rewrite",
                "command": {
                    "title": "TermOrganism: Preview suggestions",
                    "command": "termorganism.previewFixes",
                    "arguments": [uri],
                }
            })

        return actions

    def run(self) -> int:
        while True:
            msg = self._read()
            if msg is None:
                return 0

            method = msg.get("method")
            msg_id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                self._send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "capabilities": {
                            "textDocumentSync": 1,
                            "codeActionProvider": True,
                        },
                        "serverInfo": {
                            "name": "termorganism-lsp",
                            "version": "0.2.0",
                        },
                    },
                })
                continue

            if method == "initialized":
                continue

            if method == "shutdown":
                self.shutdown_requested = True
                self._send({"jsonrpc": "2.0", "id": msg_id, "result": None})
                continue

            if method == "exit":
                return 0 if self.shutdown_requested else 1

            if method == "textDocument/didOpen":
                td = params.get("textDocument", {})
                uri = td.get("uri")
                text = td.get("text", "")
                if uri:
                    self.documents[uri] = text
                    self._publish_diagnostics(uri, text)
                continue

            if method == "textDocument/didChange":
                td = params.get("textDocument", {})
                uri = td.get("uri")
                changes = params.get("contentChanges", [])
                if uri and changes:
                    text = changes[-1].get("text", "")
                    self.documents[uri] = text
                    self._publish_diagnostics(uri, text)
                continue

            if method == "textDocument/didSave":
                td = params.get("textDocument", {})
                uri = td.get("uri")
                if uri and uri in self.documents:
                    self._publish_diagnostics(uri, self.documents[uri])
                continue

            if method == "textDocument/codeAction":
                td = params.get("textDocument", {})
                uri = td.get("uri")
                result = self._code_actions(uri) if uri else []
                self._send({"jsonrpc": "2.0", "id": msg_id, "result": result})
                continue

            if msg_id is not None:
                self._send({"jsonrpc": "2.0", "id": msg_id, "result": None})


def main() -> int:
    return LSPServer().run()


if __name__ == "__main__":
    raise SystemExit(main())
