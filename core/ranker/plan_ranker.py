from __future__ import annotations

from typing import Any


def _strategy_semantic_weight(strategy: str) -> float:
    strategy = str(strategy or "")
    if strategy == "guard_exists":
        return 1.00
    if strategy == "try_except_recovery":
        return 0.72
    if strategy == "touch_only":
        return 0.18
    return 0.10


def _infer_strategy(plan: dict[str, Any]) -> str:
    evidence = plan.get("evidence", {}) or {}
    strategy = str(evidence.get("strategy", "") or "").strip()
    if strategy and strategy != "unknown":
        return strategy

    edits = plan.get("edits", []) or []
    if edits:
        first = edits[0]
        kind = str(first.get("kind", "") or "")
        code = str(first.get("candidate_code", "") or "")

        if kind == "operational":
            return "touch_only"
        if 'exists() else ""' in code:
            return "guard_exists"
        if "except FileNotFoundError" in code:
            return "try_except_recovery"

    return "unknown"


def _has_code_edit(plan: dict[str, Any]) -> bool:
    for edit in plan.get("edits", []) or []:
        if edit.get("kind") == "replace_full" and str(edit.get("candidate_code", "") or "").strip():
            return True
    return False


def _rank_tuple(plan: dict[str, Any]):
    evidence = dict(plan.get("evidence", {}) or {})
    strategy = _infer_strategy(plan)
    evidence["strategy"] = strategy
    plan["evidence"] = evidence

    confidence = float(plan.get("confidence", 0.0) or 0.0)
    risk = float(plan.get("risk", 0.0) or 0.0)
    blast_radius = float(plan.get("blast_radius", 0.0) or 0.0)

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}

    has_code = _has_code_edit(plan)
    multifile = evidence.get("multifile") is True

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_score = float(contract.get("score", 0.0) or 0.0)
    propagation_score = float(propagation.get("score", 0.0) or 0.0)
    semantic_bonus = _strategy_semantic_weight(strategy) * 0.90
    multifile_bonus = 0.20 if multifile else 0.0
    code_bonus = 0.55 if has_code else -0.45

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    final_score = (
        confidence
        + branch_bonus
        + contract_score
        + propagation_score
        + semantic_bonus
        + multifile_bonus
        + code_bonus
        - risk
        - blast_radius
        - complexity_penalty
    )

    semantic_priority = {
        "guard_exists": 3,
        "try_except_recovery": 2,
        "touch_only": 1,
        "unknown": 0,
    }.get(strategy, 0)

    return (
        has_code,
        contract_score,
        propagation_score,
        semantic_priority,
        round(final_score, 6),
    )


def annotate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    rt = _rank_tuple(plan)
    out = dict(plan)
    out["rank_tuple"] = list(rt)
    out["plan_score"] = float(rt[-1])
    return out


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = [annotate_plan(dict(p)) for p in (plans or [])]
    annotated.sort(key=lambda p: tuple(p.get("rank_tuple", [])), reverse=True)
    return annotated
