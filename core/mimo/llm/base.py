from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class LLMMessage:
    def __init__(self, role: str, content: str, **kwargs: Any) -> None:
        self.role = role
        self.content = content
        self.extra = kwargs

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, **self.extra}


class LLMResponse:
    def __init__(self, content: str, tool_calls: list[dict[str, Any]] | None = None,
                 usage: dict[str, int] | None = None, model: str = "") -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage = usage or {}
        self.model = model


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
