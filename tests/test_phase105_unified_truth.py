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

planner = res.get("planner") or {}
best = res.get("best_plan") or {}
ev = best.get("evidence") or {}

print(json.dumps({
    "best_plan_id": best.get("plan_id"),
    "strategy": ev.get("strategy"),
    "plan_score": best.get("plan_score"),
    "rank_tuple": best.get("rank_tuple"),
    "provider": ev.get("provider"),
    "caller": ev.get("caller"),
    "top_8": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "plan_score": p.get("plan_score"),
            "rank_tuple": p.get("rank_tuple"),
        }
        for p in (planner.get("repair_plans") or [])[:8]
    ],
}, indent=2, ensure_ascii=False))
