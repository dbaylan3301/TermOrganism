from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any


MIMO_BIN = os.getenv("MIMO_BIN", shutil.which("mimo") or "mimo")
MIMO_TIMEOUT = float(os.getenv("MIMO_TIMEOUT", "30"))


def _run_mimo(prompt: str, *, system: str = "", timeout: float | None = None) -> str:
    timeout = timeout or MIMO_TIMEOUT
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    cmd = [MIMO_BIN, "run", "--", full_prompt, "--trust"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "MIMOCODE": "1"},
            cwd=os.getenv("TERMORGANISM_CWD", os.getcwd()),
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            response_lines = []
            for line in lines:
                if line.startswith("█") or line.startswith("⠀") or not line.strip():
                    continue
                if "> build" in line or "> plan" in line or "> compose" in line:
                    continue
                response_lines.append(line)
            return "\n".join(response_lines).strip()
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    return ""


def generate_natural_response(
    *,
    user_message: str,
    context: dict[str, Any],
    intent: str = "",
    data: dict[str, Any] | None = None,
) -> str:
    data = data or {}

    system = (
        "Sen TermOrganism'in doğal dil yanıt üreteçisisin. "
        "Kullanıcının mesajını anla, bağlamı değerlendir ve doğal, samimi Türkçe cümlelerle yanıt ver. "
        "Teknik terimleri açıkla, uzun yazma. Maksimum 3-4 cümle yaz. "
        "Kullanıcıyla doğal bir sohbet yap."
    )

    prompt_parts = [f"Kullanıcı mesajı: {user_message}"]

    if intent:
        prompt_parts.append(f"Niyet: {intent}")

    if data.get("answer"):
        prompt_parts.append(f"Mevcut yanıt: {data['answer']}")

    if data.get("repair"):
        repair = data["repair"]
        if isinstance(repair, dict) and repair.get("ok"):
            prompt_parts.append("Onarım başarılı oldu.")
        else:
            prompt_parts.append("Onarım başarısız oldu.")

    if data.get("timed_out"):
        prompt_parts.append("İşlem zaman aşımına uğradı.")

    prompt_parts.append("\nDoğal bir Türkçe yanıt ver.")
    prompt = "\n".join(prompt_parts)

    response = _run_mimo(prompt, system=system, timeout=25)
    if response and len(response) > 15:
        return response

    return ""


def chat_with_mimo(
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
    system: str = "",
) -> str:
    system = system or (
        "Sen TermOrganism'sin. Doğal Türkçe ile konuş. "
        "Kullanıcının sorularını anla, yardımcı ol. "
        "Kısa ve net yanıtlar ver."
    )

    cmd_parts = ["--print", "--system", system]

    if history:
        for h in history[-5:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role == "user":
                cmd_parts.extend(["--user", content])
            elif role == "assistant":
                cmd_parts.extend(["--assistant", content])

    cmd_parts.extend(["--user", message])

    cmd = [MIMO_BIN] + cmd_parts

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "MIMOCODE": "1"},
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return ""
