from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Tool


class EditTool(Tool):
    def name(self) -> str:
        return "edit"

    def description(self) -> str:
        return "Edit a file by replacing exact text. Use for precise modifications."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file",
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact text to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "Text to replace with",
                },
                "replaceAll": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default false)",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(self, file_path: str = "", old_string: str = "",
                      new_string: str = "", replaceAll: bool = False,
                      **kwargs: Any) -> str:
        path = Path(file_path)
        if not path.exists():
            return f"Error: file not found: {file_path}"

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

        if old_string not in content:
            return f"Error: old_string not found in {file_path}"

        if replaceAll:
            count = content.count(old_string)
            content = content.replace(old_string, new_string)
            path.write_text(content, encoding="utf-8")
            return f"Replaced {count} occurrences in {file_path}"
        else:
            if content.count(old_string) > 1:
                return f"Error: old_string found multiple times in {file_path}. Use replaceAll=true or provide more context."
            content = content.replace(old_string, new_string, 1)
            path.write_text(content, encoding="utf-8")
            return f"Edited {file_path}"
