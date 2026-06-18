from __future__ import annotations

import subprocess
from typing import Any

from . import Tool


class GrepTool(Tool):
    def name(self) -> str:
        return "grep"

    def description(self) -> str:
        return "Search file contents using regex. Returns matching lines with file paths."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in",
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g. '*.py')",
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str = "", path: str | None = None,
                      include: str | None = None, **kwargs: Any) -> str:
        cmd = ["grep", "-rn", "--color=never", pattern]
        if include:
            cmd.extend(["--include", include])
        cmd.append(path or ".")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, cwd=path or "."
            )
            output = result.stdout.strip()
            if not output:
                return f"No matches for '{pattern}'"
            lines = output.splitlines()
            if len(lines) > 100:
                return "\n".join(lines[:100]) + f"\n\n({len(lines)} total matches, showing first 100)"
            return output
        except subprocess.TimeoutExpired:
            return "Error: grep timed out"
        except Exception as e:
            return f"Error: {e}"
