from __future__ import annotations

import json
import subprocess
import sys


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def main():
    baseline = run(["./termorganism", "demo/cross_file_dep.py", "--json"])
    forced = run(["./termorganism", "demo/cross_file_dep.py", "--json", "--force-semantic"])

    baseline_json = json.loads(baseline["stdout"])
    forced_json = json.loads(forced["stdout"])

    print(json.dumps({
        "baseline_ok": baseline_json.get("ok"),
        "baseline_message": baseline_json.get("message"),
        "forced_has_best_plan": bool(forced_json.get("best_plan")),
        "forced_best_plan_id": (forced_json.get("best_plan") or {}).get("plan_id"),
        "forced_strategy": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("strategy")),
        "forced_provider": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("provider")),
        "forced_caller": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("caller")),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
