from __future__ import annotations

from typing import Any


def top_live_whisper(whispers: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    rows = whispers or []
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda x: (float(x.get("priority", 0.0)), float(x.get("confidence", 0.0))),
        reverse=True,
    )[0]


def derive_runtime_whispers(
    *,
    signature: str | None = None,
    error_text: str | None = None,
) -> list[dict[str, Any]]:
    sig = str(signature or "").lower()
    err = str(error_text or "").lower()

    rows: list[dict[str, Any]] = []

    if "importerror" in sig or "module" in sig or "no_module_named" in sig:
        rows.append({
            "kind": "import-risk",
            "priority": 0.84,
            "confidence": 0.92,
            "message": "runtime repro import zincirinin kırıldığını gösteriyor",
        })

    if "filenotfounderror" in sig or "no such file or directory" in err:
        rows.append({
            "kind": "path-risk",
            "priority": 0.80,
            "confidence": 0.90,
            "message": "runtime repro dosya yolunun kırıldığını gösteriyor",
        })

    if "syntaxerror" in sig or "syntax error" in err:
        rows.append({
            "kind": "syntax-risk",
            "priority": 0.91,
            "confidence": 0.96,
            "message": "runtime repro sözdizimi kırılması gösteriyor",
        })

    return rows


def merge_whispers(
    static_whispers: list[dict[str, Any]] | None,
    runtime_whispers: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in (static_whispers or []) + (runtime_whispers or []):
        kind = str(item.get("kind", "") or "")
        msg = str(item.get("message", "") or "")
        key = (kind, msg)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    merged.sort(
        key=lambda x: (float(x.get("priority", 0.0)), float(x.get("confidence", 0.0))),
        reverse=True,
    )
    return merged


def apply_live_whisper_bias(
    *,
    requested_mode: str,
    whispers: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    top = top_live_whisper(whispers)
    if not top:
        return {
            "used": False,
            "effective_mode": requested_mode,
            "kind": None,
            "priority": 0.0,
            "message": "",
            "reason": "",
            "verify_emphasis": False,
        }

    kind = str(top.get("kind", ""))
    priority = float(top.get("priority", 0.0) or 0.0)
    message = str(top.get("message", "") or "")
    effective_mode = requested_mode
    reason_parts: list[str] = []
    verify_emphasis = False

    if kind in {"syntax-risk", "import-risk", "path-risk"}:
        verify_emphasis = priority >= 0.68

        if requested_mode == "hot_force" and priority >= 0.70:
            effective_mode = "fast_v2"
            reason_parts.append("live whisper avoided hot_force")

        elif requested_mode == "fast" and priority >= 0.62:
            effective_mode = "fast_v2"
            reason_parts.append("live whisper promoted fast_v2")

        elif requested_mode == "auto" and priority >= 0.72:
            effective_mode = "fast_v2"
            reason_parts.append("live whisper stabilized auto→fast_v2")

    if verify_emphasis:
        reason_parts.append("live whisper emphasizes verify-first")

    if message:
        reason_parts.append(message)

    return {
        "used": True,
        "effective_mode": effective_mode,
        "kind": kind or None,
        "priority": round(priority, 4),
        "message": message,
        "reason": " | ".join(reason_parts),
        "verify_emphasis": verify_emphasis,
    }
