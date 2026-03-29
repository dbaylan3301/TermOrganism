from __future__ import annotations

from core.agents.base import BaseAgent, AgentTask, AgentResult


class PlannerAgent(BaseAgent):
    name = "planner"

    async def run(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "plan_id": f"plan_{task.name}",
                "intent": task.payload.get("intent", "repair"),
                "target": task.payload.get("target"),
            },
        )
