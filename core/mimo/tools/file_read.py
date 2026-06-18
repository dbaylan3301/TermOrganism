from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Tool


class FileReadTool(Tool):
    def name(self) -> str:
        return "read"

    def description(self) -> str:
        return "Read a file's contents. Returns the full content or a specific range of lines."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of lines to read",
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str = "", offset: int | None = None,
                      limit: int | None = None, **kwargs: Any) -> str:
        path = Path(file_path)
        if not path.exists():
            return f"Error: file not found: {file_path}"
        if path.is_dir():
            entries = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
            return "\n".join(entries[:200])

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"

        lines = text.splitlines()

        start = (offset - 1) if offset else 0
        end = (start + limit) if limit else len(lines)
        selected = lines[start:end]

        output_lines = []
        for i, line in enumerate(selected, start=start + 1):
            output_lines.append(f"{i}: {line}")

        total = len(lines)
        result = "\n".join(output_lines)
        if end < total:
            result += f"\n\n(Showing {start+1}-{end} of {total} lines)"
        return result
