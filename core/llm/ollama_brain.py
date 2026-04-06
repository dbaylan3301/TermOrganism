from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

try:
    from ollama import Client
    _OLLAMA_IMPORT_ERROR = ""
except Exception as e:
    Client = None
    _OLLAMA_IMPORT_ERROR = repr(e)


OLLAMA_HOST = os.getenv("TERMORGANISM_OLLAMA_HOST", "http://127.0.0.1:11434")


@dataclass(slots=True)
class ThoughtPolicy:
    label: str
    model: str
    think: bool
    temperature: float
    num_predict: int


def select_policy(task_kind: str, complexity: float = 0.5) -> ThoughtPolicy:
    task_kind = str(task_kind or "").strip().lower()

    if task_kind == "ui_only":
        return ThoughtPolicy("ui_only", "qwen3:0.6b", False, 0.2, 64)
    if task_kind == "predictive_hint":
        return ThoughtPolicy("predictive_hint", "qwen3:0.6b", False, 0.2, 80)
    if task_kind == "route_decision":
        return ThoughtPolicy("route_decision", "qwen3:1.7b", False, 0.15, 96)
    if task_kind == "repair_plan":
        return ThoughtPolicy("repair_plan", "qwen3:1.7b", False, 0.15, 120)
    if task_kind == "multi_file_repair":
        return ThoughtPolicy("multi_file_repair", "qwen3:1.7b", False, 0.1, 140)
    if task_kind == "chat_freeform":
        return ThoughtPolicy("chat_freeform", "qwen3:1.7b", False, 0.3, 160)
    if complexity >= 0.8:
        return ThoughtPolicy("fallback_hard", "qwen3:1.7b", False, 0.15, 120)
    return ThoughtPolicy("fallback", "qwen3:1.7b", False, 0.2, 80)


def _fallback_thought(task_kind: str, prompt: str, context: dict[str, Any], policy: ThoughtPolicy, error: str) -> dict[str, Any]:
    whisper_kind = str(context.get("whisper_kind") or "")
    planner_mode = str(context.get("planner_suggested_mode") or "fast_v2")

    mode_bias = "fast_v2"
    if planner_mode in {"fast", "fast_v2", "safe_preview"}:
        mode_bias = planner_mode
    if whisper_kind == "path-risk":
        mode_bias = "fast_v2"

    return {
        "stance": "cautious",
        "confidence": 0.31,
        "summary": "Ollama yanıt vermedi; deterministik policy ile devam ediliyor.",
        "next_action": "fallback_to_existing_logic",
        "why": [
            "local ollama unavailable or unsupported runtime path",
            "repair path must stay responsive",
        ],
        "mode_bias": mode_bias,
        "verify_first": True,
        "_ollama": {
            "policy": policy.label,
            "model": policy.model,
            "think": policy.think,
            "temperature": policy.temperature,
            "num_predict": policy.num_predict,
            "available": False,
            "error": error,
        },
    }


def _extract_json_block(text: str) -> dict[str, Any] | None:
    text = str(text or "").strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r'\{.*\}', text, flags=re.S)
    if not m:
        return None

    blob = m.group(0)
    try:
        return json.loads(blob)
    except Exception:
        return None


def _msg_content(resp: Any) -> str:
    if isinstance(resp, dict):
        msg = resp.get("message") or {}
        if isinstance(msg, dict):
            return str(msg.get("content") or "")
        if "response" in resp:
            return str(resp.get("response") or "")
    try:
        msg = getattr(resp, "message", None)
        if msg is not None:
            content = getattr(msg, "content", None)
            if content is not None:
                return str(content)
    except Exception:
        pass
    try:
        response = getattr(resp, "response", None)
        if response is not None:
            return str(response)
    except Exception:
        pass
    return ""


def _normalize_parsed(parsed: dict[str, Any], *, policy: ThoughtPolicy) -> dict[str, Any]:
    out = {
        "stance": str(parsed.get("stance") or "balanced"),
        "confidence": float(parsed.get("confidence", 0.3) or 0.3),
        "summary": str(parsed.get("summary") or "").strip(),
        "next_action": str(parsed.get("next_action") or "fallback_to_existing_logic"),
        "why": list(parsed.get("why") or []),
        "mode_bias": str(parsed.get("mode_bias") or "fast_v2"),
        "verify_first": bool(parsed.get("verify_first", True)),
    }
    out["_ollama"] = {
        "policy": policy.label,
        "model": policy.model,
        "think": policy.think,
        "temperature": policy.temperature,
        "num_predict": policy.num_predict,
        "available": True,
    }
    return out


def generate_thought(
    *,
    task_kind: str,
    prompt: str,
    context: dict[str, Any] | None = None,
    complexity: float = 0.5,
) -> dict[str, Any]:
    context = context or {}
    policy = select_policy(task_kind, complexity)

    if Client is None:
        return _fallback_thought(task_kind, prompt, context, policy, f"python_client_missing: {_OLLAMA_IMPORT_ERROR}")

    try:
        client = Client(host=OLLAMA_HOST)
    except Exception as e:
        return _fallback_thought(task_kind, prompt, context, policy, repr(e))

    system = (
        "You are TermOrganism's local reasoning layer. "
        "Return only compact JSON. "
        "Schema keys: stance, confidence, summary, next_action, why, mode_bias, verify_first. "
        "Prefer verification and controllable edits."
    )

    user_obj = {
        "task_kind": task_kind,
        "context": context,
        "prompt": prompt,
    }

    # 1) chat
    try:
        resp = client.chat(
            model=policy.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)},
            ],
            options={
                "temperature": policy.temperature,
                "num_predict": policy.num_predict,
            },
        )
        msg = _msg_content(resp)
        parsed = _extract_json_block(msg)
        if parsed:
            out = _normalize_parsed(parsed, policy=policy)
            out["_ollama"]["transport"] = "python_client_chat"
            return out
    except Exception:
        pass

    # 2) generate
    try:
        gen_prompt = (
            f"{system}\n\n"
            "Return only valid JSON.\n\n"
            f"{json.dumps(user_obj, ensure_ascii=False)}"
        )
        resp = client.generate(
            model=policy.model,
            prompt=gen_prompt,
            options={
                "temperature": policy.temperature,
                "num_predict": policy.num_predict,
            },
        )
        msg = _msg_content(resp)
        parsed = _extract_json_block(msg)
        if parsed:
            out = _normalize_parsed(parsed, policy=policy)
            out["_ollama"]["transport"] = "python_client_generate"
            return out
    except Exception as e:
        return _fallback_thought(task_kind, prompt, context, policy, repr(e))

    return {
        "stance": "balanced",
        "confidence": 0.3,
        "summary": "Ollama cevap verdi ama yapılandırılmış JSON çıkarmadı.",
        "next_action": "fallback_to_existing_logic",
        "why": ["model output was non-json"],
        "mode_bias": "fast_v2",
        "verify_first": True,
        "_ollama": {
            "policy": policy.label,
            "model": policy.model,
            "think": policy.think,
            "temperature": policy.temperature,
            "num_predict": policy.num_predict,
            "available": True,
            "transport": "python_client_non_json",
        },
    }
