from __future__ import annotations

import os
import re
from typing import Any

try:
    from ollama import Client
    _OLLAMA_IMPORT_ERROR = ""
except Exception as e:
    Client = None
    _OLLAMA_IMPORT_ERROR = repr(e)


OLLAMA_HOST = os.getenv("TERMORGANISM_OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_TEXT_MODEL = os.getenv("TERMORGANISM_OLLAMA_TEXT_MODEL", "qwen3:1.7b")


def _client() -> Client | None:
    if Client is None:
        return None
    try:
        return Client(host=OLLAMA_HOST)
    except Exception:
        return None


def _clean_text(text: str, fallback: str) -> str:
    t = str(text or "").strip()
    if not t:
        return fallback
    return " ".join(t.split())


def _sameish(a: str, b: str) -> bool:
    aa = re.sub(r"\s+", " ", a.strip().lower())
    bb = re.sub(r"\s+", " ", b.strip().lower())
    return aa == bb


def _local_whisper_fallback(base: str, context: dict[str, Any]) -> str:
    kind = str(context.get("whisper_kind") or "")
    if kind == "path-risk":
        return "Dosya yolu runtime sırasında kırılıyor olabilir; verify-first daha güvenli."
    if kind == "import-risk":
        return "Import zinciri bu ortamda eksik görünüyor; dependency doğrulaması iyi olur."
    if kind == "bare-except-risk":
        return "Bare except gerçek hatayı maskeleyebilir; daha dar exception yakalamak safer."
    return base


def _local_narration_fallback(base: str, context: dict[str, Any]) -> str:
    mode = str(context.get("mode") or "")
    if mode == "local_narration":
        return f"Durum safer route yönüne kaymış görünüyor. {base}"
    return base


def _generate_text(system: str, prompt: str, *, fallback: str, temperature: float = 0.45, num_predict: int = 128) -> str:
    client = _client()
    if client is None:
        return fallback

    try:
        resp = client.chat(
            model=OLLAMA_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": temperature,
                "num_predict": num_predict,
            },
        )
        msg = None
        if isinstance(resp, dict):
            msg = ((resp.get("message") or {}).get("content"))
        else:
            msg = getattr(getattr(resp, "message", None), "content", None)
        return _clean_text(str(msg or ""), fallback)
    except Exception:
        return fallback


def vary_whisper_message(base_message: str, *, context: dict[str, Any] | None = None) -> str:
    base = _clean_text(base_message, "")
    if not base:
        return ""

    context = context or {}
    prompt = (
        "Aşağıdaki teknik whisper mesajını yeniden yaz.\n"
        "Kurallar:\n"
        "- Türkçe yaz\n"
        "- tek cümle yaz\n"
        "- aynı metni tekrar etme\n"
        "- teknik anlamı koru\n"
        "- daha doğal ve operasyonel yap\n"
        "- 'verify-first', 'safer', 'kontrol', 'doğrula' gibi kısa yön verici dil kullanabilirsin\n\n"
        f"Bağlam: {context}\n"
        f"Orijinal: {base}"
    )
    system = (
        "You rewrite runtime whisper messages. "
        "Do not copy the original sentence verbatim. "
        "Keep it short, actionable, and semantically faithful."
    )
    out = _generate_text(system, prompt, fallback=base, temperature=0.5, num_predict=72)
    if _sameish(out, base):
        return _local_whisper_fallback(base, context)
    return out


def vary_narration_text(base_text: str, *, context: dict[str, Any] | None = None) -> str:
    base = _clean_text(base_text, "")
    if not base:
        return ""

    context = context or {}
    prompt = (
        "Aşağıdaki anlatımı yeniden yaz.\n"
        "Kurallar:\n"
        "- Türkçe yaz\n"
        "- 1 veya 2 cümle olsun\n"
        "- aynı metni tekrar etme\n"
        "- daha akıcı ve profesyonel yap\n"
        "- teknik anlamı koru\n"
        "- daha güçlü ifade kullan ama uzatma\n\n"
        f"Bağlam: {context}\n"
        f"Orijinal: {base}"
    )
    system = (
        "You rewrite short runtime narration for a developer tool. "
        "Do not echo the source sentence verbatim. "
        "Make it more fluid and professional while keeping the technical meaning."
    )
    out = _generate_text(system, prompt, fallback=base, temperature=0.55, num_predict=96)
    if _sameish(out, base):
        return _local_narration_fallback(base, context)
    return out


def variation_status() -> dict[str, Any]:
    return {
        "client_available": Client is not None,
        "import_error": _OLLAMA_IMPORT_ERROR,
        "host": OLLAMA_HOST,
        "model": OLLAMA_TEXT_MODEL,
    }
