from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class HotPattern:
    repair: str
    confidence_boost: float
    apply_direct: bool = True


HOT_PATTERNS: dict[str, HotPattern] = {
    "filenotfounderror:open:runtime": HotPattern(
        repair="add_existence_check",
        confidence_boost=0.15,
        apply_direct=True,
    ),
    "importerror:no_module_named": HotPattern(
        repair="install_or_fix_import",
        confidence_boost=0.20,
        apply_direct=True,
    ),
}


def _normalize_hot_signature(error_text: str) -> str:
    low = (error_text or "").lower()

    if "filenotfounderror" in low:
        if "open(" in low or "read_text" in low or "no such file or directory" in low:
            return "filenotfounderror:open:runtime"

    if "modulenotfounderror" in low or "no module named" in low or "importerror" in low:
        return "importerror:no_module_named"

    return hashlib.sha256(low.encode("utf-8")).hexdigest()[:24]


def boost_confidence(base_confidence: float, error_text: str) -> dict[str, Any]:
    sig = _normalize_hot_signature(error_text)
    pat = HOT_PATTERNS.get(sig)

    if not pat:
        return {
            "confidence": float(base_confidence or 0.0),
            "recommendation": "human_review",
            "source": "none",
            "signature": sig,
        }

    new_conf = min(0.98, float(base_confidence or 0.0) + float(pat.confidence_boost or 0.0))
    return {
        "confidence": new_conf,
        "recommendation": "auto_apply" if pat.apply_direct and new_conf > 0.90 else "human_review",
        "source": "hot_cache",
        "signature": sig,
        "repair": pat.repair,
    }
