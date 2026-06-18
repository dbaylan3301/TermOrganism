from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Tool


class GlobTool(Tool):
    def name(self) -> str:
        return "glob"

    def description(self) -> str:
        return "Find files matching a glob pattern. Returns matching file paths."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str = "", path: str | None = None,
                      **kwargs: Any) -> str:
        base = Path(path) if path else Path.cwd()
        try:
            matches = sorted(str(p) for p in base.glob(pattern))
            if not matches:
                return f"No files matching '{pattern}' in {base}"
            return "\n".join(matches[:200])
        except Exception as e:
            return f"Error: {e}"
