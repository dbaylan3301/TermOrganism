from __future__ import annotations

from core.agents.base import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"unknown agent: {name}")
        return self._agents[name]

    def names(self) -> list[str]:
        return sorted(self._agents.keys())
