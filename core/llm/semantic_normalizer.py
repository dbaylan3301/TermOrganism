from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

OLLAMA_URL = os.getenv("TERMORGANISM_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("TERMORGANISM_SEMANTIC_MODEL", "qwen3:1.7b")
OLLAMA_TIMEOUT = float(os.getenv("TERMORGANISM_SEMANTIC_TIMEOUT", "1.8"))
OLLAMA_ENABLE = str(os.getenv("TERMORGANISM_SEMANTIC_OLLAMA", "1")).strip().lower() not in {"0","false","no","off"}

_SCHEMA_KEYS = [
    "intent_family",
    "user_goal",
    "target_scope",
    "operation_mode",
    "risk_level",
    "needs_repo_context",
    "needs_execution",
    "needs_clarification",
    "ambiguity_note",
    "recommended_route",
    "confidence",
    "constraints",
    "evidence",
    "language",
]

def _extract_json(text: str) -> dict[str, Any] | None:
    text = str(text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end+1])
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None

def normalize_with_ollama(message: str) -> dict[str, Any] | None:
    if not OLLAMA_ENABLE:
        return None

    prompt = f"""
You are a semantic task normalizer for a developer terminal assistant.

Return ONLY one JSON object.
No markdown. No prose. No code fences.

Allowed intent_family values:
repo_summary, repo_gap, architecture_review, weakness_analysis, productization, roadmap,
test_strategy, diagnose, repair_request, help, general_analysis

Allowed operation_mode values:
read_only, preview_first, execute

Allowed risk_level values:
low, medium, high

Interpret this user message:
{message!r}

Return JSON with keys exactly:
{_SCHEMA_KEYS}

Rules:
- If user asks to explain / summarize a codebase or project, use repo_summary.
- If user asks what is missing / gaps / eksik / eksikler, use repo_gap.
- If user asks why project is weak / fragile / kırılgan, use weakness_analysis.
- If user asks productization / next steps / roadmap, use productization or roadmap.
- If user asks test strategy, use test_strategy.
- If user asks to fix / repair / patch something, use repair_request and preview_first by default.
- Prefer read_only unless explicit action is requested.
- Keep confidence realistic between 0.55 and 0.98.
- constraints and evidence must be arrays of short strings.
- language should be "tr" if the message is Turkish, otherwise "en".
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.05,
            "num_predict": 180,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode("utf-8", "ignore"))
    except Exception:
        return None

    text = raw.get("response") or raw.get("message", {}).get("content") or ""
    out = _extract_json(text)
    if not out:
        return None

    # basic shape cleanup
    cleaned = {k: out.get(k) for k in _SCHEMA_KEYS}
    if not isinstance(cleaned.get("constraints"), list):
        cleaned["constraints"] = []
    if not isinstance(cleaned.get("evidence"), list):
        cleaned["evidence"] = []
    try:
        cleaned["confidence"] = float(cleaned.get("confidence", 0.6) or 0.6)
    except Exception:
        cleaned["confidence"] = 0.6
    return cleaned
