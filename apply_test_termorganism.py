from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path
import json

from core.autofix import run_autofix

ROOT = Path.cwd()
DEMO = ROOT / "demo"

syntax_path = DEMO / "broken_syntax_apply.py"
syntax_path.write_text("def mul(a, b)\n    return a * b\n", encoding="utf-8")

error_text = (
    "Traceback (most recent call last):\n"
    f'  File "{syntax_path}", line 1\n'
    "    def mul(a, b)\n"
    "                 ^\n"
    "SyntaxError: expected ':'"
)

result = run_autofix(error_text=error_text, file_path=str(syntax_path), auto_apply=True)

print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
print("\n--- file content after apply ---")
print(syntax_path.read_text(encoding="utf-8", errors="replace"))
