from __future__ import annotations

from core.agents.base import BaseAgent, AgentTask, AgentResult


class TestRunnerAgent(BaseAgent):
    name = "test_runner"

    async def run(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "command": task.payload.get("command", ""),
                "status": "not_executed_yet",
            },
        )
