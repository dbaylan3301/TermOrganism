from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess
import sys


@dataclass
class BehavioralVerifyResult:
    ok: bool
    mode: str
    reason: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_python_runtime(file_path: str | Path) -> BehavioralVerifyResult:
    p = Path(file_path).resolve()
    workdir = p.parent.resolve()
    cmd = [sys.executable, p.name]

    proc = subprocess.run(
        cmd,
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )

    ok = proc.returncode == 0
    return BehavioralVerifyResult(
        ok=ok,
        mode="python_runtime",
        reason="runtime execution passed" if ok else "runtime execution failed",
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )


def verify_repro_delta(before_stderr: str, after_stderr: str) -> BehavioralVerifyResult:
    before = (before_stderr or "").strip()
    after = (after_stderr or "").strip()

    if before and not after:
        return BehavioralVerifyResult(
            ok=True,
            mode="repro_delta",
            reason="previous failure disappeared after candidate application",
        )

    if before != after:
        return BehavioralVerifyResult(
            ok=True,
            mode="repro_delta",
            reason="failure signature changed after candidate application",
            stderr=after,
        )

    return BehavioralVerifyResult(
        ok=False,
        mode="repro_delta",
        reason="failure signature unchanged",
        stderr=after,
    )
