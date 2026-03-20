#!/usr/bin/env python3
from __future__ import annotations

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
