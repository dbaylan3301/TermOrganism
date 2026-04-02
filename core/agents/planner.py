from __future__ import annotations

from pathlib import Path
from core.agents.base import BaseAgent, AgentTask, AgentResult


class PlannerAgent(BaseAgent):
    name = "planner"

    def _infer_from_file(self, target: str | None) -> str:
        if not target:
            return "fast"
        try:
            source = Path(target).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return "fast"

        lowered = source.lower()
        if "open(" in lowered and ".read()" in lowered:
            return "hot_force"
        if "read_text(" in lowered:
            return "hot_force"
        if "import " in lowered or "from " in lowered:
            return "fast_v2"
        return "fast"

    async def run(self, task: AgentTask) -> AgentResult:
        intent = str(task.payload.get("intent", "repair"))
        target = task.payload.get("target")
        error_text = str(task.payload.get("error_text", "")).lower()

        suggested_mode = intent
        if intent == "auto":
            if "filenotfounderror" in error_text or "no such file or directory" in error_text:
                suggested_mode = "hot_force"
            elif "modulenotfounderror" in error_text or "no module named" in error_text or "importerror" in error_text:
                suggested_mode = "fast_v2"
            else:
                suggested_mode = self._infer_from_file(target)

        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "plan_id": f"plan_{task.name}",
                "intent": intent,
                "target": target,
                "suggested_mode": suggested_mode,
                "reason": "signature-guided routing",
            },
        )
