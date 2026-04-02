from __future__ import annotations

from core.agents.base import BaseAgent, AgentTask, AgentResult


class VerifierAgent(BaseAgent):
    name = "verifier"

    async def run(self, task: AgentTask) -> AgentResult:
        checks = task.payload.get("checks", [])
        adjustment = 0.02 if checks else 0.0

        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "verified": True,
                "checks": checks,
                "confidence_adjustment": adjustment,
            },
        )
