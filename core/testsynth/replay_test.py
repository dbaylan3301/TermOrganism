from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess
import sys

from core.repro.project_workspace import build_temp_workspace


@dataclass
class ReplayTestResult:
    ok: bool
    mode: str
    reason: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    workspace_root: str = ""
    temp_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_python_replay(file_path: str | Path, candidate_code: str | None = None, target_file: str | None = None) -> ReplayTestResult:
    base_file = target_file or file_path
    tmp, layout = build_temp_workspace(base_file)
    try:
        temp_target = Path(layout.target_dst)
        if candidate_code is not None and candidate_code.strip():
            temp_target.write_text(candidate_code, encoding="utf-8")

        rel_target = temp_target.relative_to(Path(layout.workspace_root))

        proc = subprocess.run(
            [sys.executable, str(rel_target)],
            cwd=str(layout.workspace_root),
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        return ReplayTestResult(
            ok=ok,
            mode="python_replay",
            reason="replay execution passed" if ok else "replay execution failed",
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            workspace_root=layout.workspace_root,
            temp_target=str(temp_target),
        )
    finally:
        tmp.cleanup()
