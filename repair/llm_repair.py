import os
import requests

API = os.getenv("GROQ_API_KEY")
URL = "https://api.groq.com/openai/v1/chat/completions"

def repair(error: str, code: str):
    if not API:
        return {"ok": False, "reason": "missing GROQ_API_KEY", "fixed": None}

    payload = {
        "model": "llama-3.3-70b-versatile",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You fix broken Python code. "
                    "Return ONLY the corrected Python source code. "
                    "Do not use markdown fences. "
                    "Do not explain anything."
                ),
            },
            {
                "role": "user",
                "content": f"Error:\\n{error}\\n\\nCode:\\n{code}",
            },
        ],
    }

    try:
        r = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {API}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
    except Exception as e:
        return {"ok": False, "reason": f"request failed: {e}", "fixed": None}

    if r.status_code != 200:
        body = r.text[:1000]
        return {
            "ok": False,
            "reason": f"http {r.status_code}: {body}",
            "fixed": None,
        }

    try:
        data = r.json()
        text = data["choices"][0]["message"]["content"]
    except Exception as e:
        return {"ok": False, "reason": f"bad response parse: {e}", "fixed": None}

    if not text or not text.strip():
        return {"ok": False, "reason": "empty model output", "fixed": None}

    fixed = text.strip()

    # markdown code fence temizliği
    if fixed.startswith("```"):
        lines = fixed.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        fixed = "\\n".join(lines).strip()

    return {"ok": True, "reason": "ok", "fixed": fixed}
