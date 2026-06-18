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
  File "/usr/lib/python3.13/pathlib/_local.py", line 548, in read_text
    return PathBase.read_text(self, encoding, errors, newline)
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

res = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

planner = res.get("planner") or {}
best = res.get("best_plan") or {}
best_edit = ((best.get("edits") or [{}])[0])

print(json.dumps({
    "candidate_count": planner.get("candidate_count"),
    "base_plan_count": planner.get("base_plan_count"),
    "multifile_plan_count": planner.get("multifile_plan_count"),
    "best_plan_id": best.get("plan_id"),
    "strategy": (best.get("evidence") or {}).get("strategy"),
    "best_kind": best_edit.get("kind"),
    "best_has_candidate_code": bool((best_edit.get("candidate_code", "") or "").strip()),
    "best_target_file": best_edit.get("file"),
    "top_8": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "kind": ((p.get("edits") or [{}])[0]).get("kind"),
            "has_candidate_code": bool((((p.get("edits") or [{}])[0]).get("candidate_code", "") or "").strip()),
            "target_file": ((p.get("edits") or [{}])[0]).get("file"),
            "rank_tuple": p.get("rank_tuple"),
        }
        for p in (planner.get("repair_plans") or [])[:8]
    ],
}, indent=2, ensure_ascii=False))
