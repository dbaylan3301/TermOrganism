from __future__ import annotations

import re
from typing import Any

from core.chat.task_spec import TaskSpec
from core.llm.semantic_normalizer import normalize_with_ollama


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


FAMILIES: list[tuple[str, list[str], str, str, bool]] = [
    ("repo_gap", [
        "ne eksik", "neler eksik", "eksikler", "missing", "gaps", "what's missing",
        "what is missing", "hangi eksikler", "hangi boşluklar", "hangi açıklar"
    ], "repo zayıflıklarını ve eksiklerini bul", "read_only", False),

    ("repo_summary", [
        "repo ne yapıyor", "bu repo ne yapıyor", "proje ne yapıyor",
        "bu projeyi açıkla", "projeyi açıkla", "bu projeyi özetle", "projeyi özetle",
        "bu kod tabanını açıkla", "kod tabanını açıkla", "repo özeti", "summary"
    ], "repo özeti ver", "read_only", False),

    ("architecture_review", [
        "mimari", "architecture", "architectural", "tasarım", "design", "yapı nasıl", "mimariyi değerlendir"
    ], "mimari değerlendirme yap", "read_only", False),

    ("weakness_analysis", [
        "neden kırılgan", "weakness", "zayıflık", "fragile", "riskli taraf", "neresi kötü",
        "neden zayıf", "hangi tarafı kırılgan", "neden sağlam değil"
    ], "zayıf alanları teşhis et", "read_only", False),

    ("productization", [
        "ürünleşt", "productize", "productization", "nasıl ürün olur", "go to market",
        "ürün yapmak", "ürünleşme", "ürünleştirmek", "ürüne çevirmek"
    ], "ürünleşme önerisi ver", "read_only", False),

    ("roadmap", [
        "roadmap", "sonraki adım", "next steps", "bundan sonra", "öncelik sırası", "ne yapmalıyız sırayla"
    ], "ilerleme sırası öner", "read_only", False),

    ("test_strategy", [
        "test stratejisi", "test strategy", "nasıl test", "hangi test", "test planı", "nasıl doğrularız"
    ], "test stratejisi öner", "read_only", False),

    ("diagnose", [
        "neden fast_v2", "neden böyle seçildi", "why fast_v2", "neden bu rota", "neden bu karar"
    ], "karar mantığını teşhis et", "read_only", False),

    ("repair_request", [
        "düzelt", "fix", "repair", "onar", "patchle", "uygula", "çöz"
    ], "güvenli repair isteğini değerlendir", "preview_first", True),

    ("help", [
        "ne işe yarıyor", "what does", "yardım", "help", "nasıl çalışıyor"
    ], "özellik açıklaması yap", "read_only", False),
]


def _heuristic_spec(message: str) -> TaskSpec:
    text = _norm(message)

    best_family = "general_analysis"
    best_goal = "soruyu anlamlandır ve en güvenli yanıt yolunu seç"
    best_mode = "read_only"
    best_exec = False
    best_hits: list[str] = []

    for family, patterns, goal, mode, needs_exec in FAMILIES:
        hits = [p for p in patterns if p in text]
        if len(hits) > len(best_hits):
            best_hits = hits
            best_family = family
            best_goal = goal
            best_mode = mode
            best_exec = needs_exec

    ambiguity = ""
    conf = 0.62
    if best_hits:
        conf = min(0.94, 0.78 + 0.08 * len(best_hits))
    else:
        ambiguity = "mesaj belirgin bir aileye güçlü biçimde oturmadı; genel analiz moduna düşüldü"

    return TaskSpec(
        raw_message=message,
        intent_family=best_family,
        user_goal=best_goal,
        target_scope="repo",
        operation_mode=best_mode,
        risk_level="medium" if best_exec else "low",
        needs_repo_context=True,
        needs_execution=best_exec,
        needs_clarification=False,
        ambiguity_note=ambiguity,
        recommended_route="semantic_preview_first" if best_exec else "semantic_readonly",
        confidence=conf,
        constraints=[],
        evidence=best_hits or ["heuristic_fallback"],
        language="tr" if re.search(r"[çğıöşü]|\\b(ve|bu|projede|neden|nasıl|ne)\\b", text) else "en",
    )


def interpret_message(message: str) -> TaskSpec:
    heuristic = _heuristic_spec(message)

    # If strong enough, trust deterministic route
    if heuristic.confidence >= 0.88 and heuristic.intent_family != "general_analysis":
        return heuristic

    # Otherwise ask Ollama to normalize, then merge conservatively
    llm = normalize_with_ollama(message)
    if not llm:
        return heuristic

    intent_family = str(llm.get("intent_family") or heuristic.intent_family or "general_analysis")
    user_goal = str(llm.get("user_goal") or heuristic.user_goal)
    operation_mode = str(llm.get("operation_mode") or heuristic.operation_mode or "read_only")
    needs_execution = bool(llm.get("needs_execution", operation_mode in {"preview_first", "execute"}))
    try:
        conf = float(llm.get("confidence", heuristic.confidence) or heuristic.confidence)
    except Exception:
        conf = heuristic.confidence

    merged = TaskSpec(
        raw_message=message,
        intent_family=intent_family,
        user_goal=user_goal,
        target_scope=str(llm.get("target_scope") or heuristic.target_scope),
        operation_mode=operation_mode,
        risk_level=str(llm.get("risk_level") or ("medium" if needs_execution else "low")),
        needs_repo_context=bool(llm.get("needs_repo_context", True)),
        needs_execution=needs_execution,
        needs_clarification=bool(llm.get("needs_clarification", False)),
        ambiguity_note=str(llm.get("ambiguity_note") or heuristic.ambiguity_note),
        recommended_route=str(llm.get("recommended_route") or ("semantic_preview_first" if needs_execution else "semantic_readonly")),
        confidence=max(heuristic.confidence, min(conf, 0.96)) if heuristic.intent_family == intent_family else min(conf, 0.93),
        constraints=list(llm.get("constraints") or []),
        evidence=list(heuristic.evidence) + list(llm.get("evidence") or ["ollama_normalized"]),
        language=str(llm.get("language") or heuristic.language),
    )
    return merged
