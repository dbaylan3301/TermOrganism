#!/usr/bin/env python3
from pathlib import Path
from core.autofix import run_autofix
import json

demo = Path("demo")
demo.mkdir(exist_ok=True)

(demo / "cross_file_dep.py").write_text(
    'from helper_mod import read_log\n\nprint(read_log())\n',
    encoding="utf-8",
)
(demo / "helper_mod.py").write_text(
    'from pathlib import Path\n\ndef read_log():\n    return Path("logs/app.log").read_text()\n',
    encoding="utf-8",
)

error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

result = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "best_target_file": (result.get("result") or {}).get("target_file"),
    "best_scope": (result.get("result") or {}).get("affected_scope"),
    "candidate_count": result.get("candidate_count"),
    "candidate_targets": [
        {
            "summary": c.get("summary"),
            "target_file": c.get("target_file"),
            "scope": c.get("affected_scope"),
            "strategy": (c.get("metadata") or {}).get("strategy"),
        }
        for c in result.get("candidates", [])
    ],
}, ensure_ascii=False, indent=2))
