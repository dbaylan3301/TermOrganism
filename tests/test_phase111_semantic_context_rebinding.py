from __future__ import annotations

import json
import subprocess


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def main():
    forced = run(["./termorganism", "demo/cross_file_dep.py", "--json", "--force-semantic"])
    payload = json.loads(forced["stdout"])

    best = payload.get("best_plan") or {}
    ev = best.get("evidence") or {}
    best_edit = ((best.get("edits") or [{}])[0])

    print(json.dumps({
        "forced_has_best_plan": bool(best),
        "forced_best_plan_id": best.get("plan_id"),
        "forced_strategy": ev.get("strategy"),
        "forced_provider": ev.get("provider"),
        "forced_caller": ev.get("caller"),
        "forced_best_kind": best_edit.get("kind"),
        "forced_has_candidate_code": bool((best_edit.get("candidate_code", "") or "").strip()),
        "forced_target_file": best_edit.get("file"),
        "forced_rank_tuple": best.get("rank_tuple"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
