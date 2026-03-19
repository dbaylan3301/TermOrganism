#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
DEMO = ROOT / "demo"
DEMO.mkdir(exist_ok=True)

fixtures = {
    "broken_syntax.py": """def add(a, b)
    return a + b
""",
    "broken_import.py": """import definitely_missing_package_12345

print("hello")
""",
    "broken_runtime.py": """from pathlib import Path

print(Path("logs/app.log").read_text())
""",
    "broken_shell.txt": """bash: mycustomtool: command not found
""",
}

for name, content in fixtures.items():
    path = DEMO / name
    path.write_text(content, encoding="utf-8")
    print(f"[WRITE] {path}")

print("\\nDone.")
