from __future__ import annotations

import inspect
import os
from time import perf_counter
from pathlib import Path
from typing import Any

from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.util.logging import get_logger

from .utils import build_semantic_prelude
from .candidates import build_candidates
from .planner import build_and_rank_plans
from .verify import verify_repair
from .hot_cache import apply_hot_cache_to_payload
from .events import emit_thought, EventStoreAdapter

logger = get_logger("repair.engine")


def _ms(start: float, end: float) -> float:
    return round((end - start) * 1000.0, 3)


def _call_analyze_failure_causes_compat(
    *,
    error_text: str,
    semantic: dict[str, Any],
    project_graph: Any,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    try:
        params = inspect.signature(analyze_failure_causes).parameters
    except Exception:
        params = {}

    kwargs: dict[str, Any] = {
        "error_text": error_text,
        "semantic": semantic,
        "project_graph": project_graph,
    }
    if "file_path" in params:
        kwargs["file_path"] = file_path

    result = analyze_failure_causes(**kwargs)

    if isinstance(result, list):
        return result
    return [r.to_dict() for r in result]


def _maybe_execute_plan(plan: dict[str, Any], file_path: str | None) -> dict[str, Any] | None:
    if not file_path:
        return None
    try:
        from core.planner.branch_executor import execute_repair_plan
        return execute_repair_plan(plan, file_path)
    except Exception:
        return None


def repair(
    error_text: str,
    file_path: str | None = None,
    fast: bool = False,
    thought_bus: Any = None,
) -> dict[str, Any]:
    t0 = perf_counter()
    logger.info("Repair started for %s (fast=%s)", file_path, fast)

    emit_thought(
        thought_bus,
        "Input",
        f"target={file_path or '<none>'}",
        kind="info",
    )

    semantic = build_semantic_prelude(error_text=error_text, file_path=file_path)
    t_semantic = perf_counter()

    repro = (semantic or {}).get("repro") or {}
    loc = (semantic or {}).get("localization") or {}
    top = loc.get("top") or {}

    repro_msg = (
        "forced semantic mode: runtime repro skipped"
        if repro.get("exception_type") == "ForcedSemanticAnalysis"
        else (
            f"reproduced={repro.get('reproduced')} "
            f"returncode={repro.get('returncode')} "
            f"exception={repro.get('exception_type')}"
        )
    )
    emit_thought(
        thought_bus,
        "Reproduction",
        repro_msg,
        kind="success" if repro.get("ok") or repro.get("exception_type") == "ForcedSemanticAnalysis" else "warn",
    )

    if top:
        emit_thought(
            thought_bus,
            "Fault Localization",
            f"top={top.get('file_path')} reason={top.get('reason')}",
            kind="info",
            confidence=top.get("score"),
            file_path=top.get("file_path"),
            line_no=top.get("line_no"),
        )

    graph = build_project_graph(file_path).to_dict() if file_path else {
        "project_root": str("."),
        "files": [],
        "adjacency": {},
    }
    causes = _call_analyze_failure_causes_compat(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
        file_path=file_path,
    )

    candidates = build_candidates(
        error_text=error_text,
        file_path=file_path,
        semantic=semantic,
        thought_bus=thought_bus,
    )

    ranked_plans = build_and_rank_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
        candidates=candidates,
        file_path=file_path,
        thought_bus=thought_bus,
        execute_plan_fn=_maybe_execute_plan,
    )

    best_plan = ranked_plans[0] if ranked_plans else None

    if best_plan:
        evidence = best_plan.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = (
            ((best_plan.get("edits") or [{}])[0].get("file"))
            or best_plan.get("target_file")
        )
        logger.info("Best plan selected: strategy=%s target=%s", strategy, target)
        emit_thought(
            thought_bus,
            "Final Selection",
            f"strategy={strategy} target={target}",
            kind="success",
            confidence=best_plan.get("confidence"),
            file_path=target,
        )
    else:
        logger.warning("No best plan selected for %s", file_path)
        emit_thought(
            thought_bus,
            "Final Selection",
            "no best plan selected",
            kind="fail",
        )

    verify_result: dict[str, Any] = {"ok": False, "reason": "no verification performed"}
    if best_plan and file_path:
        try:
            verify_result = verify_repair(
                plan=best_plan,
                file_path=file_path,
                error_text=error_text,
            )
        except Exception as exc:
            verify_result = {"ok": False, "reason": f"verify exception: {exc}"}

    elapsed_ms = _ms(t0, perf_counter())

    payload: dict[str, Any] = {
        "ok": bool(verify_result.get("ok")),
        "run_id": None,
        "error_text": error_text,
        "file_path": file_path,
        "elapsed_ms": elapsed_ms,
        "ranked_plans": ranked_plans,
        "best_plan": best_plan,
        "verify": verify_result,
        "semantic": semantic,
        "candidates_count": len(candidates),
        "causes_count": len(causes),
    }

    payload = apply_hot_cache_to_payload(payload, error_text=error_text)

    try:
        EventStoreAdapter().append_event(payload)
    except Exception:
        pass

    emit_thought(
        thought_bus,
        "Completion",
        f"elapsed_ms={elapsed_ms} ok={payload['ok']}",
        kind="success" if payload["ok"] else "warn",
    )

    logger.info("Repair completed in %.2fms ok=%s", elapsed_ms, payload["ok"])

    return payload
