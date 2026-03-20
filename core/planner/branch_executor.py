from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess
import sys

from core.repro.project_workspace import build_temp_workspace
from core.verify.python_verify import verify_python


@dataclass
class BranchExecutionResult:
    ok: bool
    reason: str
    applied_files: list[str]
    workspace_root: str
    runtime: dict[str, Any]
    static_verify: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _force_file_path(path: Path, entry_file: str, workspace_root: Path) -> Path:
    entry_name = Path(entry_file).name or "target.py"

    if path == workspace_root:
        return workspace_root / entry_name

    if str(path) in {"", "."}:
        return workspace_root / entry_name

    if path.exists() and path.is_dir():
        return path / entry_name

    # suffix yoksa ve mevcut parent/workspace mantığında klasör gibi görünüyorsa entry adı ekle
    if path.suffix == "" and path.name == workspace_root.name:
        return workspace_root / entry_name

    return path


def execute_repair_plan(plan: dict[str, Any], entry_file: str) -> dict[str, Any]:
    tmp, layout = build_temp_workspace(entry_file)
    try:
        workspace_root = Path(layout.workspace_root)
        project_root = Path(layout.project_root)

        entry_abs = Path(entry_file).resolve()
        try:
            rel_entry = entry_abs.relative_to(project_root)
        except Exception:
            rel_entry = Path(entry_abs.name)

        entry_dst = workspace_root / rel_entry
        entry_dst = _force_file_path(entry_dst, entry_file, workspace_root)

        applied_files: list[str] = []
        static_verify: dict[str, Any] | None = None

        for edit in plan.get("edits", []):
            if edit.get("kind") == "replace_full":
                code = edit.get("candidate_code", "") or ""
                target = edit.get("file")

                dst = entry_dst
                if target:
                    try:
                        target_abs = Path(target).resolve()
                        rel = target_abs.relative_to(project_root)
                        candidate = workspace_root / rel
                        if rel != Path(".") and str(rel) != "":
                            dst = candidate
                    except Exception:
                        dst = entry_dst

                dst = _force_file_path(dst, entry_file, workspace_root)

                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(code, encoding="utf-8")
                applied_files.append(str(dst))

                if dst.suffix == ".py":
                    static_verify = verify_python(code)

            elif edit.get("kind") == "operational":
                for cmd in edit.get("commands", []):
                    if cmd.startswith("mkdir -p "):
                        folder = cmd[len("mkdir -p "):].strip()
                        (workspace_root / folder).mkdir(parents=True, exist_ok=True)
                    elif cmd.startswith("touch "):
                        file_rel = cmd[len("touch "):].strip()
                        p = workspace_root / file_rel
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.touch()

        runtime_proc = subprocess.run(
            [sys.executable, str(rel_entry)],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
        )

        runtime = {
            "ok": runtime_proc.returncode == 0,
            "returncode": runtime_proc.returncode,
            "stdout": runtime_proc.stdout or "",
            "stderr": runtime_proc.stderr or "",
        }

        ok = runtime["ok"] and (static_verify is None or static_verify.get("ok", False))
        reason = "plan branch execution passed" if ok else "plan branch execution failed"

        return BranchExecutionResult(
            ok=ok,
            reason=reason,
            applied_files=applied_files,
            workspace_root=str(workspace_root),
            runtime=runtime,
            static_verify=static_verify,
        ).to_dict()
    finally:
        tmp.cleanup()
