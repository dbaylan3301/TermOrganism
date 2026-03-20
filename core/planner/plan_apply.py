from __future__ import annotations

from pathlib import Path
from typing import Any

from core.util.patch_apply import make_backup
from core.planner.edit_ops import apply_edit
from core.verify.python_verify import verify_python


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    edits = plan.get("edits", []) or []
    backups: list[str] = []
    applied: list[dict[str, Any]] = []

    for edit in edits:
        file_path = edit.get("file")
        if file_path and Path(file_path).exists():
            backups.append(str(make_backup(file_path)))

        res = apply_edit(edit)
        applied.append(res)
        if not res.get("ok"):
            return {
                "applied": False,
                "reason": res.get("reason", "edit failed"),
                "backups": backups,
                "results": applied,
            }

        if edit.get("kind") == "replace_full":
            code = edit.get("candidate_code", "") or ""
            py_ok = verify_python(code)
            if not py_ok.get("ok", False):
                return {
                    "applied": False,
                    "reason": f"post-apply static verify failed: {py_ok.get('reason', '')}",
                    "backups": backups,
                    "results": applied,
                    "verify": py_ok,
                }

    return {
        "applied": True,
        "reason": "plan applied and verified",
        "backups": backups,
        "results": applied,
    }
