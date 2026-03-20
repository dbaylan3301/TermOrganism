from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class ReproResult:
    ok: bool
    command: list[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    exception_type: str = ""
    reproduced: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_python_file(file_path: str | Path, cwd: str | Path | None = None) -> ReproResult:
    p = Path(file_path).resolve()
    workdir = Path(cwd).resolve() if cwd else p.parent.resolve()

    if workdir == p.parent:
        target = p.name
    else:
        target = str(p)

    cmd = [sys.executable, target]

    proc = subprocess.run(
        cmd,
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )

    stderr = proc.stderr or ""
    stdout = proc.stdout or ""
    reproduced = proc.returncode != 0

    exc_type = ""
    for line in reversed(stderr.splitlines()):
        if ":" in line:
            exc_type = line.split(":", 1)[0].strip()
            break

    return ReproResult(
        ok=(proc.returncode == 0),
        command=cmd,
        cwd=str(workdir),
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        exception_type=exc_type,
        reproduced=reproduced,
    )


def run_shell_text(error_text: str) -> ReproResult:
    return ReproResult(
        ok=False,
        command=[],
        cwd=str(Path.cwd()),
        returncode=1,
        stdout="",
        stderr=error_text,
        exception_type="ShellError",
        reproduced=True,
    )
