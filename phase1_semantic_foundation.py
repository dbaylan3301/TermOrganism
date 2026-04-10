from __future__ import annotations
from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/repro/__init__.py": '''"""Reproduction layer for semantic repair."""\n''',

    "core/repro/harness.py": '''from __future__ import annotations

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
    p = Path(file_path)
    workdir = str(Path(cwd) if cwd else p.parent)
    cmd = [sys.executable, str(p)]

    proc = subprocess.run(
        cmd,
        cwd=workdir,
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
        cwd=workdir,
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
''',

    "core/semantic/__init__.py": '''"""Semantic localization layer."""\n''',

    "core/semantic/fault_localizer.py": '''from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Suspicion:
    file_path: str
    line_no: int | None
    symbol: str | None
    reason: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_traceback_file_and_line(error_text: str) -> tuple[str | None, int | None]:
    patterns = [
        r'File "([^"]+)", line (\\d+)',
        r"File '([^']+)', line (\\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, error_text or "")
        if m:
            return m.group(1), int(m.group(2))
    return None, None


def _infer_reason(error_text: str) -> tuple[str, float]:
    text = (error_text or "").lower()

    if "syntaxerror" in text:
        return "syntax failure near reported line", 0.95
    if "indentationerror" in text:
        return "indentation failure near reported line", 0.95
    if "modulenotfounderror" in text or "no module named" in text:
        return "dependency/import failure at module import boundary", 0.84
    if "filenotfounderror" in text or "no such file or directory" in text:
        return "runtime path/file access failure", 0.82
    if "permission denied" in text:
        return "permission boundary failure", 0.78
    if "command not found" in text:
        return "shell executable resolution failure", 0.76

    return "generic localized failure", 0.50


def localize_fault(error_text: str, file_path: str | None = None) -> list[Suspicion]:
    tb_file, tb_line = _extract_traceback_file_and_line(error_text)
    reason, score = _infer_reason(error_text)

    chosen_file = tb_file or file_path or ""
    if not chosen_file:
        return [Suspicion(file_path="", line_no=None, symbol=None, reason=reason, score=score)]

    return [
        Suspicion(
            file_path=chosen_file,
            line_no=tb_line,
            symbol=None,
            reason=reason,
            score=score,
        )
    ]


def summarize_suspicions(items: list[Suspicion]) -> dict[str, Any]:
    return {
        "count": len(items),
        "top": items[0].to_dict() if items else None,
        "items": [x.to_dict() for x in items],
    }
''',

    "core/verify/behavioral_verify.py": '''from __future__ import annotations

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
    p = Path(file_path)
    proc = subprocess.run(
        [sys.executable, str(p)],
        cwd=str(p.parent),
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
''',

    "core/models/schemas.py": '''from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SemanticRepairCandidate:
    expert: str
    kind: str
    confidence: float
    summary: str
    candidate_code: str = ""
    patch: str | None = None
    hypothesis: str = ""
    semantic_claim: str = ""
    affected_scope: list[str] = field(default_factory=list)
    repro_fix_score: float = 0.0
    regression_score: float = 0.0
    blast_radius: float = 0.0
    risk: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
''',

    "semantic_probe.py": '''#!/usr/bin/env python3

import json
from pathlib import Path

from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions

ROOT = Path.cwd()
DEMO = ROOT / "demo"

cases = [
    DEMO / "broken_syntax.py",
    DEMO / "broken_import.py",
    DEMO / "broken_runtime.py",
]

for case in cases:
    if not case.exists():
        continue
    repro = run_python_file(case)
    susp = localize_fault(repro.stderr, file_path=str(case))
    payload = {
        "case": str(case),
        "repro": repro.to_dict(),
        "localization": summarize_suspicions(susp),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

shell_error = "zsh: command not found: bat"
susp = localize_fault(shell_error, file_path="demo/broken_shell_bat.txt")
print(json.dumps({
    "case": "shell",
    "repro": run_shell_text(shell_error).to_dict(),
    "localization": summarize_suspicions(susp),
}, ensure_ascii=False, indent=2))
''',
}


def backup_and_write(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        print(f"[BACKUP] {rel_path} -> {backup.relative_to(ROOT)}")

    path.write_text(content, encoding="utf-8")
    print(f"[WRITE]  {rel_path}")


def main() -> int:
    for rel_path, content in PATCHES.items():
        backup_and_write(rel_path, content)
    print("\\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
