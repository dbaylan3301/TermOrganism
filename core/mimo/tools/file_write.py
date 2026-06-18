from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Tool


class FileWriteTool(Tool):
    def name(self) -> str:
        return "write"

    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, file_path: str = "", content: str = "", **kwargs: Any) -> str:
        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Written {len(content)} bytes to {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"
