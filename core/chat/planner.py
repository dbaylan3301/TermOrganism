from __future__ import annotations

from typing import Any

from .interpreter import ChatIntent
from .session import ChatSessionState


def build_plan(intent: ChatIntent, ctx, session: ChatSessionState) -> dict[str, Any]:
    goal = intent.goal
    explain_first = bool(intent.flags.get("explain"))
    auto_apply = bool(intent.flags.get("auto"))
    safe_mode = bool(intent.flags.get("safe"))

    if goal == "confirm_pending":
        pending = session.pending_action or {}
        return {
            "goal": "confirm_pending",
            "steps": [
                "bekleyen eylemi okuyacağım",
                "onaylanan işi güvenli sınırlar içinde çalıştıracağım",
                "sonucu açıklayacağım",
            ],
            "risk": pending.get("risk", "medium"),
            "confirmation_required": False,
        }

    if goal == "cancel_pending":
        return {
            "goal": "cancel_pending",
            "steps": [
                "bekleyen eylemi iptal edeceğim",
                "session state'i temizleyeceğim",
            ],
            "risk": "low",
            "confirmation_required": False,
        }

    if goal == "repo_summary":
        return {
            "goal": goal,
            "steps": [
                "README ve üst seviye repo yapısını okuyacağım",
                "repo tipini çıkaracağım",
                "insan diliyle özet döneceğim",
            ],
            "risk": "low",
            "confirmation_required": False,
        }

    if goal == "repo_status":
        return {
            "goal": goal,
            "steps": [
                "git durumunu okuyacağım",
                "branch ve değişiklik özetini döneceğim",
            ],
            "risk": "low",
            "confirmation_required": False,
        }

    if goal in {"run_tests", "run_tests_narrow"}:
        return {
            "goal": goal,
            "steps": [
                "repo bağlamına göre test stratejisi seçeceğim",
                "gerekirse daha dar veya kısa koşu kullanacağım",
                "timeout veya fail durumunu temiz biçimde özetleyeceğim",
            ],
            "risk": "low",
            "confirmation_required": False,
        }

    if goal == "run_project":
        return {
            "goal": goal,
            "steps": [
                "repo tipini ve giriş noktasını çıkaracağım",
                "uygun çalıştırma komutunu seçeceğim",
                "komutu çalıştırıp sonucu döneceğim",
            ],
            "risk": "medium",
            "confirmation_required": safe_mode,
        }

    if goal in {"repair", "diagnose"}:
        steps = [
            "hedef dosya yolunu çıkaracağım",
            "termorganism repair hattına delege edeceğim",
            "sonucu insan diliyle özetleyeceğim",
        ]
        confirmation_required = explain_first and not auto_apply
        if confirmation_required:
            steps.insert(1, "önce güvenli repair planını önizleme olarak sunacağım")
        return {
            "goal": goal,
            "steps": steps,
            "risk": "medium",
            "confirmation_required": confirmation_required,
            "preview_only": confirmation_required,
        }

    return {
        "goal": "help",
        "steps": [
            "niyeti sınıflandıracağım",
            "uygun komutu veya analizi seçeceğim",
            "sonucu açıklayacağım",
        ],
        "risk": "low",
        "confirmation_required": False,
    }
