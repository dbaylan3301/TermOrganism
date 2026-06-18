from __future__ import annotations

import json
from typing import Any

from .llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from .llm.router import create_provider
from .tools.registry import ToolRegistry, create_default_registry
from .context import AgentContext
from .parser import parse_tool_calls
from .memory.session import SessionMemory
from .config import get_config


class Agent:
    def __init__(self, provider_name: str | None = None) -> None:
        self._config = get_config()
        self._provider = create_provider(provider_name)
        self._tools = create_default_registry()
        self._context = AgentContext()
        self._session = SessionMemory()
        self._max_turns = 20

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def context(self) -> AgentContext:
        return self._context

    def _build_messages(self, user_message: str) -> list[LLMMessage]:
        messages = [LLMMessage(role="system", content=self._context.get_system_prompt())]

        for msg in self._session.get_messages():
            messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        messages.append(LLMMessage(role="user", content=user_message))
        return messages

    async def process(self, user_message: str, callback: Any = None) -> str:
        self._session.add_message("user", user_message)
        messages = self._build_messages(user_message)

        for turn in range(self._max_turns):
            response = await self._provider.chat(
                messages=messages,
                tools=self._tools.to_schemas(),
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            if response.tool_calls:
                self._session.add_message("assistant", response.content or "[tool calls]")

                tool_results = []
                for tc in response.tool_calls:
                    name = tc["name"]
                    args = tc["arguments"]

                    if callback:
                        await callback("tool_start", name, args)

                    result = await self._tools.execute(name, **args)
                    tool_results.append({"tool_call_id": tc["id"], "content": result})

                    if callback:
                        await callback("tool_end", name, result)

                messages.append(LLMMessage(role="assistant", content=response.content or "", tool_calls=response.tool_calls))

                for tr in tool_results:
                    messages.append(LLMMessage(role="tool", content=tr["content"]))

                continue

            if response.content:
                self._session.add_message("assistant", response.content)
                return response.content

            return "(no response)"

        return "(max turns reached)"

    async def process_stream(self, user_message: str, callback: Any = None) -> str:
        self._session.add_message("user", user_message)
        messages = self._build_messages(user_message)

        full_response = ""
        async for chunk in self._provider.chat_stream(
            messages=messages,
            tools=self._tools.to_schemas(),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        ):
            full_response += chunk
            if callback:
                await callback("stream", chunk)

        clean, tool_calls = parse_tool_calls(full_response)

        if tool_calls:
            results = []
            for tc in tool_calls:
                name = tc.get("tool", tc.get("name", ""))
                args = tc.get("args", tc.get("arguments", {}))
                if callback:
                    await callback("tool_start", name, args)
                result = await self._tools.execute(name, **args)
                results.append(result)
                if callback:
                    await callback("tool_end", name, result)

            follow_up = await self.process(
                f"Tool results:\n" + "\n".join(f"Tool: {tc.get('tool', tc.get('name', ''))}\nResult: {r}" for tc, r in zip(tool_calls, results)),
                callback=callback,
            )
            return follow_up

        self._session.add_message("assistant", clean)
        return clean

    def clear_session(self) -> None:
        self._session.clear()
