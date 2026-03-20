from __future__ import annotations

from typing import Any


def plan_to_candidate(plan: dict[str, Any]) -> dict[str, Any]:
    edits = plan.get("edits", []) or []
    first_edit = edits[0] if edits else {}

    evidence = plan.get("evidence", {}) or {}
    target_files = plan.get("target_files", []) or []
    target_file = target_files[0] if target_files else first_edit.get("file")

    patch = None
    if first_edit.get("kind") == "operational":
        cmds = first_edit.get("commands", []) or []
        patch = " && ".join(cmds) if cmds else None
    elif first_edit.get("kind") == "replace_full":
        ev_strategy = evidence.get("strategy", "")
        if ev_strategy in {"guard_exists", "try_except_recovery"}:
            patch = "mkdir -p logs && touch logs/app.log"

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}

    return {
        "expert": "planner",
        "kind": "runtime_file_missing",
        "confidence": float(plan.get("confidence", 0.0) or 0.0),
        "summary": first_edit.get("summary", plan.get("hypothesis", "repair plan")),
        "patch": patch,
        "candidate_code": first_edit.get("candidate_code", "") or "",
        "file_path_hint": target_file,
        "target_file": target_file,
        "hypothesis": plan.get("hypothesis", ""),
        "semantic_claim": "plan-first multi-file repair selection",
        "affected_scope": target_files,
        "metadata": {
            "strategy": evidence.get("strategy", ""),
            "plan_id": plan.get("plan_id", ""),
            "multifile": evidence.get("multifile", False),
            "caller": evidence.get("caller"),
            "provider": evidence.get("provider"),
        },
        "repro_fix_score": 0.75 if branch.get("ok") else 0.0,
        "regression_score": float(contract.get("score", 0.0) or 0.0) * 0.65,
        "synth_test_score": float(contract.get("score", 0.0) or 0.0),
        "historical_success_prior": 0.0,
        "blast_radius": float(plan.get("blast_radius", 0.0) or 0.0),
        "branch_result": branch,
        "contract_result": contract,
        "contract_propagation": propagation,
        "source_plan": plan,
    }
