from __future__ import annotations

import asyncio
from core.agents.base import AgentTask, AgentResult
from core.agents.registry import AgentRegistry


class AgentScheduler:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    async def run_many(self, plan: list[tuple[str, AgentTask]]) -> list[AgentResult]:
        coros = [self.registry.get(name).run(task) for name, task in plan]
        return await asyncio.gather(*coros)
