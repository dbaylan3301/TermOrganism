from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.1:70b") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=300.0)

    def name(self) -> str:
        return f"ollama/{self._model}"

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        converted = []
        for m in messages:
            converted.append({"role": m.role, "content": m.content})
        return converted

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = [
                {"type": "function", "function": t["function"]} for t in tools
            ]

        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = []
        for tc in message.get("tool_calls", []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn["arguments"]) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
            except (json.JSONDecodeError, TypeError):
                args = {}
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "name": fn.get("name", ""),
                "arguments": args,
            })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage={"total_tokens": data.get("eval_count", 0)},
            model=self._model,
        )

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 16384,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        async with self._client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    if "message" in chunk:
                        content = chunk["message"].get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        await self._client.aclose()
