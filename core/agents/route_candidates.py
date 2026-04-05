from __future__ import annotations

from typing import Any


RISK_MAP = {
    "hot_force": "high",
    "fast_v2": "medium",
    "fast": "medium",
    "repair_plan": "low",
    "safe_preview": "low",
    "verify_first": "low",
}


def _risk(route: str) -> str:
    return RISK_MAP.get(str(route or ""), "medium")


def _score_from_risk(route: str) -> float:
    risk = _risk(route)
    if risk == "low":
        return 0.72
    if risk == "high":
        return 0.58
    return 0.66


def build_route_candidates(
    *,
    planner: dict[str, Any] | None,
    current_effective_mode: str,
    bridge_apply: dict[str, Any] | None = None,
    whisper_apply: dict[str, Any] | None = None,
    intent_ctx: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    planner = planner or {}
    bridge_apply = bridge_apply or {}
    whisper_apply = whisper_apply or {}
    intent_ctx = intent_ctx or {}

    candidates: list[dict[str, Any]] = []

    planner_mode = str(planner.get("suggested_mode") or current_effective_mode or "fast")
    planner_reason = str(planner.get("reason") or "planner suggested mode")
    candidates.append({
        "route": planner_mode,
        "source": "planner",
        "score": round(max(0.40, _score_from_risk(planner_mode) + 0.18), 4),
        "risk": _risk(planner_mode),
        "reason": planner_reason,
        "evidence": ["signature", "planner"],
    })

    bridge_route = str(bridge_apply.get("recommended_route") or "").strip()
    bridge_score = float(bridge_apply.get("score", 0.0) or 0.0)
    bridge_reason = str(bridge_apply.get("reason") or "")
    if bridge_route:
        candidates.append({
            "route": bridge_route,
            "source": "bridge",
            "score": round(max(0.35, bridge_score), 4),
            "risk": _risk(bridge_route),
            "reason": bridge_reason or "predictive→repair bridge",
            "evidence": ["bridge", "history"],
        })

    whisper_route = str(whisper_apply.get("effective_mode") or "").strip()
    whisper_prio = float(whisper_apply.get("priority", 0.0) or 0.0)
    whisper_reason = str(whisper_apply.get("reason") or "")
    if whisper_route:
        candidates.append({
            "route": whisper_route,
            "source": "whisper",
            "score": round(max(0.30, whisper_prio), 4),
            "risk": _risk(whisper_route),
            "reason": whisper_reason or "live whisper",
            "evidence": ["runtime", "whisper"],
        })

    intent_routes = list(intent_ctx.get("preload_routes") or [])
    intent_conf = float(intent_ctx.get("confidence", 0.0) or 0.0)
    if "verify_first" in intent_routes:
        candidates.append({
            "route": "fast_v2",
            "source": "intent",
            "score": round(max(0.28, 0.44 + (intent_conf * 0.25)), 4),
            "risk": _risk("fast_v2"),
            "reason": "intent-aware context prefers verify-first",
            "evidence": ["intent", "verify_first"],
        })
    if "safe_preview" in intent_routes:
        candidates.append({
            "route": "safe_preview",
            "source": "intent",
            "score": round(max(0.28, 0.40 + (intent_conf * 0.22)), 4),
            "risk": _risk("safe_preview"),
            "reason": "intent-aware context prefers preview-first",
            "evidence": ["intent", "safe_preview"],
        })

    candidates.append({
        "route": str(current_effective_mode),
        "source": "current",
        "score": round(_score_from_risk(str(current_effective_mode)), 4),
        "risk": _risk(str(current_effective_mode)),
        "reason": "current effective mode after layered adjustments",
        "evidence": ["effective_mode"],
    })

    # de-dup by (route, source)
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for item in candidates:
        key = (str(item["route"]), str(item["source"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    out.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return out
