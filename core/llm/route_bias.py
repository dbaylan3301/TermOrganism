from __future__ import annotations

import os
from typing import Any

from core.llm.ollama_brain import generate_thought


def _enabled() -> bool:
    raw = str(os.getenv("TERMORGANISM_OLLAMA_ENABLE", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def apply_ollama_route_bias(
    candidates: list[dict[str, Any]] | None,
    *,
    task_kind: str = "route_decision",
    context: dict[str, Any] | None = None,
    complexity: float = 0.6,
) -> dict[str, Any]:
    rows = [dict(x) for x in (candidates or [])]
    context = context or {}

    if not _enabled() or not rows:
        return {
            "candidates": rows,
            "thought": {
                "stance": "balanced",
                "confidence": 0.0,
                "summary": "ollama bias disabled or no candidates",
                "next_action": "keep_existing_scores",
                "why": ["disabled or empty candidates"],
                "mode_bias": "",
                "verify_first": False,
                "_ollama": {"available": False, "policy": "disabled"},
            },
        }

    planner_mode = str(context.get("planner_suggested_mode") or "")
    whisper_kind = str(context.get("whisper_kind") or "")
    bridge_score = float(context.get("bridge_score", 0.0) or 0.0)

    # kolay ve net durumlarda model çağırma
    if planner_mode in {"fast_v2", "safe_preview"} and not whisper_kind and bridge_score < 0.55:
        return {
            "candidates": rows,
            "thought": {
                "stance": "balanced",
                "confidence": 0.0,
                "summary": "ollama skipped for low-conflict route decision",
                "next_action": "keep_existing_scores",
                "why": ["low conflict route state"],
                "mode_bias": "",
                "verify_first": False,
                "_ollama": {"available": False, "policy": "skipped"},
            },
        }

    prompt = (
        "Given planner, intent, bridge, and whisper signals, choose a conservative route bias. "
        "Prefer verification and controllable edits over aggressive repair when confidence is mixed."
    )

    thought = generate_thought(
        task_kind=task_kind,
        prompt=prompt,
        context=context,
        complexity=complexity,
    )

    mode_bias = str(thought.get("mode_bias") or "").strip()
    verify_first = bool(thought.get("verify_first", False))

    out: list[dict[str, Any]] = []
    for item in rows:
        row = dict(item)
        route = str(row.get("route") or "")
        score = float(row.get("score", 0.0) or 0.0)
        notes: list[str] = []

        if mode_bias and route == mode_bias:
            score += 0.06
            notes.append(f"ollama mode_bias={mode_bias}")

        if verify_first:
            if route == "hot_force":
                score -= 0.08
                notes.append("ollama verify_first penalized hot_force")
            elif route in {"fast_v2", "safe_preview"}:
                score += 0.04
                notes.append("ollama verify_first favored safer route")

        row["score"] = round(max(0.0, min(1.0, score)), 4)

        if notes:
            base_reason = str(row.get("reason") or "")
            joined = " | ".join(notes)
            row["reason"] = f"{base_reason} | {joined}".strip(" |")
            evidence = list(row.get("evidence") or [])
            evidence.append("ollama_bias")
            row["evidence"] = evidence

        out.append(row)

    return {
        "candidates": out,
        "thought": thought,
    }
