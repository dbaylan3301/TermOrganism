from __future__ import annotations

import json
import os

import requests

from core.experts.base import RepairExpert
from core.models.schemas import FailureContext, RepairCandidate
from core.util.diffing import unified_diff


class LLMFallbackExpert(RepairExpert):
    name = "llm_fallback"
    supported_languages = {"python", "shell"}

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model

    def score(self, ctx: FailureContext) -> tuple[float, list[str]]:
        score = 0.15
        reasons = ["fallback baseline"]
        if "SyntaxError" in ctx.stderr or "Traceback" in ctx.stderr:
            score += 0.2
            reasons.append("traceback present")
        if ctx.memory_features.get("known_good_route") is None:
            score += 0.1
            reasons.append("no strong prior route")
        return min(score, 0.6), reasons

    def propose(self, ctx: FailureContext) -> list[RepairCandidate]:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return []

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a code repair expert. Preserve intent. Return JSON only with keys: "
                        "patched_code, rationale, risk, assumptions. No markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "file_path": ctx.file_path,
                            "language": ctx.language,
                            "stderr": ctx.stderr,
                            "stdout": ctx.stdout,
                            "command": ctx.command,
                            "source_code": ctx.source_code,
                        }
                    ),
                },
            ],
            "temperature": 0.1,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        patched = data.get("patched_code")
        if not patched or patched == ctx.source_code:
            return []
        return [
            RepairCandidate(
                expert_name=self.name,
                kind="llm",
                patched_code=patched,
                patch_unified_diff=unified_diff(ctx.source_code, patched, ctx.file_path, ctx.file_path),
                rationale=data.get("rationale", "llm-generated repair"),
                expert_score=0.68,
                patch_safety_score=0.55 if data.get("risk") == "medium" else 0.45 if data.get("risk") == "high" else 0.72,
                metadata={"risk": data.get("risk", "unknown"), "assumptions": data.get("assumptions", [])},
            )
        ]
