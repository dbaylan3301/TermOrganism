from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(slots=True)
class IntentResult:
    intent: str
    confidence: float
    target_hint: str | None = None
    flags: dict[str, bool] = field(default_factory=dict)


_PATH_PATTERNS = [
    r'(/[^ \t\n\r"\'`]+)',
    r'([A-Za-z0-9_.\-/]+\.(?:py|js|ts|tsx|jsx|md|json|yaml|yml|toml|ini|cfg|txt))',
]


def _extract_path(text: str) -> str | None:
    for pat in _PATH_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def classify_intent(text: str) -> IntentResult:
    raw = text.strip()
    lowered = raw.lower()

    target = _extract_path(raw)
    flags = {
        "explain": _has_any(lowered, ["açıkla", "anlat", "explain", "teach", "öğret"]),
        "safe": _has_any(lowered, ["güvenli", "safe", "risk alma"]),
        "auto": _has_any(lowered, ["otomatik", "auto", "direkt yap"]),
    }

    if _has_any(lowered, [
        "düzelt", "fix", "repair", "çöz", "sorunu çöz", "hatayı düzelt", "bu hatayı", "bir bak düzelt"
    ]):
        return IntentResult("repair", 0.93, target, flags)

    if _has_any(lowered, [
        "test", "pytest", "unit test", "integration test",
        "testleri çalıştır", "test çalıştır", "testleri başlat", "test başlat",
        "testleri koş", "test koş", "bi test", "bir test"
    ]):
        return IntentResult("run_tests", 0.90, target, flags)

    if _has_any(lowered, [
        "git durum", "repo durum", "repo ne durumda", "status", "branch", "değişiklik", "git ne alemde"
    ]):
        return IntentResult("repo_status", 0.88, target, flags)

    if _has_any(lowered, [
        "repo ne yapıyor", "bu proje ne yapıyor", "readme", "özetle", "özet çıkar", "projeyi anlat", "bu repo ne"
    ]):
        return IntentResult("repo_summary", 0.91, target, flags)

    if _has_any(lowered, [
        "çalıştır", "ayağa kaldır", "başlat", "run", "dev server", "server aç", "projeyi başlat"
    ]):
        return IntentResult("run_project", 0.87, target, flags)

    if _has_any(lowered, [
        "neden", "hata neden", "niye", "sorun ne", "problem ne", "neden patlıyor"
    ]):
        return IntentResult("diagnose", 0.84, target, flags)

    return IntentResult("help", 0.55, target, flags)
