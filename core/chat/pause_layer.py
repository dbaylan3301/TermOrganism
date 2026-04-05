from __future__ import annotations

from typing import Any


def _top_whisper(predictive_whispers: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not predictive_whispers:
        return None
    return sorted(
        predictive_whispers,
        key=lambda x: (float(x.get("priority", 0.0)), float(x.get("confidence", 0.0))),
        reverse=True,
    )[0]


def evaluate_reflective_pause(
    intent,
    plan: dict[str, Any],
    ctx,
    session,
    intent_context: dict[str, Any],
    predictive_whispers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    goal = intent.goal
    auto = bool(intent.flags.get("auto"))
    explain = bool(intent.flags.get("explain"))
    focus = str((intent_context or {}).get("focus", "general_runtime"))

    top = _top_whisper(predictive_whispers)
    top_priority = float((top or {}).get("priority", 0.0))
    top_kind = str((top or {}).get("kind", ""))
    top_message = str((top or {}).get("message", ""))

    pause: dict[str, Any] = {
        "should_pause": False,
        "force_preview": False,
        "reason": "",
        "alternatives": [],
        "focus": focus,
        "top_whisper_kind": top_kind or "-",
        "top_whisper_priority": top_priority,
        "top_whisper_message": top_message or "-",
    }

    if goal in {"repair", "diagnose"}:
        pause["should_pause"] = True
        pause["alternatives"] = ["preview_only", "diagnose_first", "apply_safe_route"]

        if auto:
            pause["reason"] = "kullanıcı otomatik uygulama istedi; sadece hafif duraksama yapılır"
            if top and top_priority >= 0.88:
                pause["reason"] += f" | güçlü predictive whisper: {top_message}"
            return pause

        if plan.get("confirmation_required") or explain:
            pause["reason"] = "açıklama/önizleme modu zaten aktif"
            if top and top_priority >= 0.72:
                pause["reason"] += f" | whisper: {top_message}"
            return pause

        if top and top_priority >= 0.70:
            pause["force_preview"] = True
            pause["reason"] = f"predictive whisper repair öncesi preview önerdi: {top_message}"
            return pause

        pause["force_preview"] = True
        pause["reason"] = "onarım öncesi niyet sorgulama katmanı preview önerdi"
        return pause

    if goal == "run_tests":
        pause["should_pause"] = True
        pause["alternatives"] = ["narrow_first", "first_failure_only", "full_suite"]

        if top and top_priority >= 0.74:
            pause["reason"] = f"predictive whisper dar test stratejisini destekliyor: {top_message}"
            return pause

        if session.last_timeout:
            pause["reason"] = "önceki test akışı timeout olduğu için dar strateji daha güvenli görünüyor"
        else:
            pause["reason"] = "test isteğinde önce hafif strateji seçmek daha güvenli"

    elif goal == "run_project":
        pause["should_pause"] = True
        pause["alternatives"] = ["inspect_entrypoint", "run_now", "explain_first"]
        if top and top_priority >= 0.80:
            pause["reason"] = f"predictive whisper önce giriş noktası doğrulaması öneriyor: {top_message}"
        else:
            pause["reason"] = "çalıştırma isteklerinde giriş noktası doğrulaması faydalı olabilir"

    elif goal in {"repo_status", "repo_summary"}:
        pause["should_pause"] = False
        pause["reason"] = "read-only analiz; duraksama gerekmiyor"

    else:
        pause["reason"] = "varsayılan akış"

    return pause
