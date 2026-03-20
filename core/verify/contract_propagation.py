from __future__ import annotations

from typing import Any


def check_contract_propagation(best_plan: dict[str, Any] | None) -> dict[str, Any]:
    if not best_plan:
        return {
            "ok": False,
            "reason": "no best_plan",
            "score": 0.0,
            "checks": [],
        }

    target_files = best_plan.get("target_files", []) or []
    edits = best_plan.get("edits", []) or []
    branch = best_plan.get("branch_result", {}) or {}
    contract = best_plan.get("contract_result", {}) or {}

    checks: list[dict[str, Any]] = []

    checks.append({
        "name": "multi_file_targeting",
        "ok": len(target_files) >= 1,
        "actual": len(target_files),
    })

    checks.append({
        "name": "edit_plan_present",
        "ok": len(edits) >= 1,
        "actual": len(edits),
    })

    checks.append({
        "name": "branch_execution_passed",
        "ok": bool(branch.get("ok", False)),
    })

    checks.append({
        "name": "contract_checks_passed",
        "ok": bool(contract.get("ok", False)),
        "actual": float(contract.get("score", 0.0) or 0.0),
    })

    score = 0.0
    weights = {
        "multi_file_targeting": 0.15,
        "edit_plan_present": 0.15,
        "branch_execution_passed": 0.35,
        "contract_checks_passed": 0.35,
    }

    for item in checks:
        if item["ok"]:
            score += weights.get(item["name"], 0.0)

    return {
        "ok": score >= 0.70,
        "reason": "contract propagation checks evaluated",
        "score": round(score, 4),
        "checks": checks,
    }
