from __future__ import annotations

from typing import Any

from . import Tool


class MemoryTool(Tool):
    def name(self) -> str:
        return "memory"

    def description(self) -> str:
        return "Search and store project memory. Recall past decisions, learnings, and context."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "store", "list"],
                    "description": "Action to perform",
                },
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "content": {
                    "type": "string",
                    "description": "Content to store",
                },
                "key": {
                    "type": "string",
                    "description": "Memory key",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str = "list", query: str | None = None,
                      content: str | None = None, key: str | None = None,
                      **kwargs: Any) -> str:
        from ..memory.project import get_project_memory
        mem = get_project_memory()

        if action == "search":
            if not query:
                return "Error: query required"
            results = mem.search(query)
            if not results:
                return f"No results for '{query}'"
            return "\n".join(f"- {r['key']}: {r['content'][:200]}" for r in results)

        elif action == "store":
            if not key or not content:
                return "Error: key and content required"
            mem.store(key, content)
            return f"Stored: {key}"

        elif action == "list":
            entries = mem.list_all()
            if not entries:
                return "No memory entries."
            return "\n".join(f"- {e['key']}: {e['content'][:100]}" for e in entries)

        return f"Unknown action: {action}"
