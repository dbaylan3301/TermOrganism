from __future__ import annotations

from typing import Any


RISK_WEIGHT = {
    "low": 0.00,
    "medium": 0.06,
    "high": 0.15,
}


def _adj_score(item: dict[str, Any]) -> float:
    score = float(item.get("score", 0.0) or 0.0)
    risk = str(item.get("risk", "medium"))
    penalty = RISK_WEIGHT.get(risk, 0.06)
    return round(score - penalty, 4)


def arbitrate_route_candidates(
    candidates: list[dict[str, Any]] | None,
    *,
    fallback_route: str,
) -> dict[str, Any]:
    rows = list(candidates or [])
    if not rows:
        return {
            "final_route": fallback_route,
            "winner": None,
            "reason": "no candidates; fallback used",
            "candidate_count": 0,
        }

    enriched = []
    for item in rows:
        row = dict(item)
        row["adjusted_score"] = _adj_score(item)
        enriched.append(row)

    enriched.sort(key=lambda x: float(x.get("adjusted_score", 0.0)), reverse=True)
    winner = enriched[0]

    reason = (
        f"winner={winner.get('route')} "
        f"source={winner.get('source')} "
        f"score={winner.get('score')} "
        f"adjusted={winner.get('adjusted_score')} "
        f"risk={winner.get('risk')}"
    )

    return {
        "final_route": str(winner.get("route") or fallback_route),
        "winner": winner,
        "reason": reason,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }
