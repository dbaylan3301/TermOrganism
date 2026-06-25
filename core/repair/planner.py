from __future__ import annotations

from typing import Any

from core.planner.repair_planner import build_repair_plans
from core.planner.multi_file_planner import expand_multifile_plan_family
from core.ranker.plan_ranker import rank_plans
from core.verify.contract_synth import synthesize_and_check_contract
from core.verify.contract_propagation import check_contract_propagation

from .events import emit_thought
from .utils import force_plan_target_to_file


def build_and_rank_plans(
    error_text: str,
    semantic: dict[str, Any] | None,
    causes: list[dict[str, Any]] | None,
    project_graph: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    file_path: str | None = None,
    thought_bus: Any = None,
    *,
    execute_plan_fn: Any = None,
) -> list[dict[str, Any]]:
    base_plans = build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=project_graph,
        candidates=candidates,
        file_path=file_path,
    )

    multifile_plans = expand_multifile_plan_family(
        base_plans=base_plans,
        file_path=file_path,
        semantic=semantic,
    )

    emit_thought(
        thought_bus,
        "Planning",
        f"base_plans={len(base_plans)} multifile_plans={len(multifile_plans)}",
        kind="info",
    )

    emit_thought(
        thought_bus,
        "Plan Expansion",
        f"total_plans={len(base_plans) + len(multifile_plans)}",
        kind="info",
    )

    all_plans = list(base_plans) + list(multifile_plans)

    enriched = []
    for plan in all_plans:
        plan = force_plan_target_to_file(plan, file_path)
        branch = execute_plan_fn(plan, file_path) if execute_plan_fn and file_path else None
        contract = synthesize_and_check_contract(
            before_error_text=error_text,
            branch_result=branch or {},
            expected_behavior=plan.get("expected_behavior", {}),
        )

        p2 = dict(plan)
        p2["branch_result"] = branch
        p2["contract_result"] = contract
        p2["contract_propagation"] = check_contract_propagation(p2)
        enriched.append(p2)

    ranked = rank_plans(enriched)

    if ranked:
        best = ranked[0]
        evidence = best.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best.get("edits") or [{}])[0].get("file")) or best.get("target_file")
        emit_thought(
            thought_bus,
            "Winner Selection",
            f"best strategy={strategy} target={target}",
            kind="success",
            confidence=best.get("confidence"),
            file_path=target,
        )
        emit_thought(
            thought_bus,
            "Plan Rejection",
            f"rejected={max(0, len(ranked) - 1)} alternate_plans={max(0, len(ranked) - 1)}",
            kind="warn" if len(ranked) > 1 else "info",
        )
    else:
        emit_thought(
            thought_bus,
            "Winner Selection",
            "no ranked plans available",
            kind="fail",
        )

    return ranked
