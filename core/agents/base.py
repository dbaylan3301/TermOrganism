from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentTask:
    name: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult:
    agent: str
    ok: bool
    output: dict[str, Any]
    error: str = ""


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, task: AgentTask) -> AgentResult:
        raise NotImplementedError
