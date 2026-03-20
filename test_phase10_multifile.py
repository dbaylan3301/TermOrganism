from __future__ import annotations

import json
from core.autofix import run_autofix

res = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
    file_path="demo/cross_file_dep.py",
)

print(json.dumps({
    "routes": res.get("routes"),
    "plan_score": res.get("plan_score"),
    "best_plan_id": (res.get("best_plan") or {}).get("plan_id"),
    "contract_propagation": res.get("contract_propagation"),
    "target_files": (res.get("best_plan") or {}).get("target_files"),
    "provider": (((res.get("best_plan") or {}).get("evidence") or {}).get("provider")),
    "caller": (((res.get("best_plan") or {}).get("evidence") or {}).get("caller")),
}, indent=2, ensure_ascii=False))
