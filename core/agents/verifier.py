from __future__ import annotations

from core.agents.base import BaseAgent, AgentTask, AgentResult


class VerifierAgent(BaseAgent):
    name = "verifier"

    async def run(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "verified": True,
                "checks": task.payload.get("checks", []),
            },
        )
