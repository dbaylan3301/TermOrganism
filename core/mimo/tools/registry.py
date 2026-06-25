from __future__ import annotations

from typing import Any

from . import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name()] = tool

    def register_all(self, tools: list[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_schemas(self) -> list[dict[str, Any]]:
        return [t.to_schema() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        return await tool.execute(**kwargs)


def create_default_registry() -> ToolRegistry:
    from .bash import BashTool
    from .file_read import FileReadTool
    from .file_write import FileWriteTool
    from .edit import EditTool
    from .glob import GlobTool
    from .grep import GrepTool
    from .git import GitTool
    from .task import TaskTool
    from .question import QuestionTool
    from .memory import MemoryTool

    registry = ToolRegistry()
    registry.register(BashTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(EditTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    registry.register(GitTool())
    registry.register(TaskTool())
    registry.register(QuestionTool())
    registry.register(MemoryTool())
    return registry
