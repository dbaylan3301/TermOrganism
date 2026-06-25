from __future__ import annotations

from typing import Any


def boost_confidence(base_score: float, error_text: str) -> dict[str, Any]:
    from core.memory.engine import MemoryEngine

    engine = MemoryEngine()
    cached = engine.find_similar(error_text, limit=3)

    if not cached:
        return {"confidence": base_score, "recommendation": "human_review", "factors": {}}

    avg_prior = sum(r.confidence for r in cached) / len(cached) if cached else 0.0
    boosted = min(base_score + avg_prior * 0.3, 0.99)

    recommendation = "auto_apply" if boosted >= 0.85 else "apply_with_review" if boosted >= 0.6 else "human_review"

    return {
        "confidence": boosted,
        "recommendation": recommendation,
        "factors": {"hot_cache_avg_prior": avg_prior, "cached_records": len(cached)},
    }


def attach_hot_cache_boost(payload: dict[str, Any], *, error_text: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    base_score = float(((payload.get("confidence") or {}).get("score")) or 0.0)
    hot = boost_confidence(base_score, error_text)

    payload.setdefault("memory", {})
    payload["memory"]["hot_cache"] = hot

    verify_ok = bool((payload.get("verify") or {}).get("ok"))
    conf = payload.get("confidence") or {}
    if verify_ok and isinstance(conf, dict):
        old_score = float(conf.get("score", 0.0) or 0.0)
        new_score = max(old_score, float(hot.get("confidence", old_score) or old_score))
        conf["score"] = new_score
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = new_score - old_score
        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

    return payload


def apply_hot_cache_to_payload(payload: dict[str, Any], *, error_text: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    payload.setdefault("memory", {})
    conf = payload.get("confidence") or {}
    if not isinstance(conf, dict):
        conf = {}
    payload["confidence"] = conf

    result = payload.get("result") or {}
    best_plan = payload.get("best_plan") or {}
    base_score = float(
        conf.get("score", 0.0)
        or (result.get("confidence") if isinstance(result, dict) else 0.0)
        or (best_plan.get("confidence") if isinstance(best_plan, dict) else 0.0)
        or 0.0
    )

    hot = boost_confidence(base_score, error_text)
    payload["memory"]["hot_cache"] = hot

    verify_ok = bool((payload.get("verify") or {}).get("ok"))
    if verify_ok:
        boosted = max(base_score, float(hot.get("confidence", base_score) or base_score))
        conf["score"] = boosted
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = boosted - base_score
        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

    return payload
