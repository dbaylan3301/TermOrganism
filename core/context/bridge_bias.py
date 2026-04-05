from __future__ import annotations

from typing import Any


def choose_bridge_bias(
    bridge_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    rows = bridge_rows or []
    if not rows:
        return {
            "used": False,
            "recommended_route": None,
            "preview_bias": False,
            "narrow_test_bias": False,
            "verify_emphasis": False,
            "reason": "",
            "score": 0.0,
        }

    best = None
    best_score = -1.0

    for row in rows:
        success_rate = float(row.get("success_rate", 0.0) or 0.0)
        total = float(row.get("total", 0.0) or 0.0)
        avg_priority = float(row.get("avg_priority", 0.0) or 0.0)
        avg_syn_prior = float(row.get("avg_syn_prior", 0.0) or 0.0)

        score = (
            (success_rate * 0.45)
            + min(0.20, total * 0.03)
            + (avg_priority * 0.20)
            + (avg_syn_prior * 0.15)
        )

        if score > best_score:
            best_score = score
            best = row

    if not best:
        return {
            "used": False,
            "recommended_route": None,
            "preview_bias": False,
            "narrow_test_bias": False,
            "verify_emphasis": False,
            "reason": "",
            "score": 0.0,
        }

    kind = str(best.get("kind", "-"))
    route_hint = str(best.get("route_hint", "-"))
    success_rate = float(best.get("success_rate", 0.0) or 0.0)
    total = int(best.get("total", 0) or 0)
    avg_priority = float(best.get("avg_priority", 0.0) or 0.0)

    preview_bias = kind in {"import-risk", "path-risk", "syntax-risk"} and avg_priority >= 0.68
    narrow_test_bias = kind in {"import-risk", "path-risk", "syntax-risk"} and avg_priority >= 0.72
    verify_emphasis = success_rate < 0.95 or avg_priority >= 0.78

    reason = (
        f"bridge bias: {kind} geçmişte route={route_hint} ile "
        f"success={round(success_rate, 4)} seen={total} avg_priority={round(avg_priority, 4)}"
    )

    return {
        "used": True,
        "recommended_route": route_hint if route_hint and route_hint != "-" else None,
        "preview_bias": preview_bias,
        "narrow_test_bias": narrow_test_bias,
        "verify_emphasis": verify_emphasis,
        "reason": reason,
        "score": round(best_score, 4),
        "source_row": best,
    }
