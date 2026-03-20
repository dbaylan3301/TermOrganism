from __future__ import annotations

from pathlib import Path
from typing import Any


def apply_edit(edit: dict[str, Any]) -> dict[str, Any]:
    file_path = edit.get("file")
    if not file_path:
        return {"ok": False, "reason": "missing edit file"}

    p = Path(file_path)
    kind = edit.get("kind", "")

    if kind == "replace_full":
        code = edit.get("candidate_code", "") or ""
        if not code.strip():
            return {"ok": False, "reason": "empty candidate_code"}
        p.write_text(code, encoding="utf-8")
        return {"ok": True, "reason": "replace_full applied", "file": str(p)}

    if kind == "operational":
        for cmd in edit.get("commands", []) or []:
            if cmd.startswith("mkdir -p "):
                folder = cmd[len("mkdir -p "):].strip()
                Path(folder).mkdir(parents=True, exist_ok=True)
            elif cmd.startswith("touch "):
                target = Path(cmd[len("touch "):].strip())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
        return {"ok": True, "reason": "operational edit applied", "file": str(p)}

    return {"ok": False, "reason": f"unsupported edit kind: {kind}"}
