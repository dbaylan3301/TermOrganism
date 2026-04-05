from __future__ import annotations

from typing import Any

from core.context.bridge_bias import choose_bridge_bias
from core.watch.predictive_engine import predictive_bridge_summary


def infer_bridge_route_bias(
    *,
    target_path: str | None,
    repo_root: str,
    focus: str,
    signature: str | None = None,
) -> dict[str, Any]:
    rows = predictive_bridge_summary(
        target_path=target_path,
        cwd=repo_root,
        focus=focus,
        signature=signature,
        limit=6,
    )
    bias = choose_bridge_bias(rows)
    bias["source_rows"] = rows
    return bias


def apply_bridge_bias_to_mode(
    *,
    requested_mode: str,
    bridge_bias: dict[str, Any] | None,
) -> dict[str, Any]:
    bias = bridge_bias or {}
    recommended = str(bias.get("recommended_route") or "").strip()
    preview_bias = bool(bias.get("preview_bias", False))
    narrow_bias = bool(bias.get("narrow_test_bias", False))
    verify_emphasis = bool(bias.get("verify_emphasis", False))
    used = bool(bias.get("used", False))

    effective_mode = requested_mode
    reason_parts: list[str] = []

    if used:
        reason_parts.append(str(bias.get("reason", "")))

    if recommended and recommended not in {"-", "unknown", "none"}:
        # conservative mapping: only override if recommendation is one of known safe route families
        safe_known = {
            "fast_v2",
            "fast",
            "repair_plan",
            "safe_preview",
            "verify_first",
        }
        if recommended in safe_known:
            effective_mode = recommended
            reason_parts.append(f"bridge recommended route={recommended}")

    if preview_bias and effective_mode not in {"safe_preview", "repair_preview"}:
        reason_parts.append("bridge suggests preview-first")
    if narrow_bias:
        reason_parts.append("bridge suggests narrower verification path")
    if verify_emphasis:
        reason_parts.append("bridge emphasizes verify-first")

    return {
        "used": used,
        "requested_mode": requested_mode,
        "effective_mode": effective_mode,
        "preview_bias": preview_bias,
        "narrow_test_bias": narrow_bias,
        "verify_emphasis": verify_emphasis,
        "recommended_route": recommended or None,
        "reason": " | ".join([x for x in reason_parts if x]) or "",
        "score": float(bias.get("score", 0.0) or 0.0),
        "source_rows": bias.get("source_rows", []),
    }
