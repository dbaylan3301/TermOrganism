from __future__ import annotations

import json
from core.autofix import run_autofix

error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

res = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

best = res.get("best_plan") or {}
ev = best.get("evidence") or {}

print(json.dumps({
    "best_plan_id": best.get("plan_id"),
    "strategy": ev.get("strategy"),
    "provider": ev.get("provider"),
    "caller": ev.get("caller"),
    "target_files": best.get("target_files"),
    "same_target_bug": ev.get("provider") == ev.get("caller"),
    "contract_propagation": res.get("contract_propagation"),
}, indent=2, ensure_ascii=False))
