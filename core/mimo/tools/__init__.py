from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name(),
                "description": self.description(),
                "parameters": self.parameters(),
            },
        }
