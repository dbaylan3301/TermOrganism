from __future__ import annotations

from core.agents.base import BaseAgent, AgentTask, AgentResult


class TestRunnerAgent(BaseAgent):
    name = "test_runner"

    async def run(self, task: AgentTask) -> AgentResult:
        command = task.payload.get("command", "")
        return AgentResult(
            agent=self.name,
            ok=True,
            output={
                "command": command,
                "status": "not_executed_yet",
                "required_checks": [command] if command else [],
            },
        )
