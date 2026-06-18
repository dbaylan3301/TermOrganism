from __future__ import annotations

import subprocess
from typing import Any

from . import Tool


class GitTool(Tool):
    def name(self) -> str:
        return "git"

    def description(self) -> str:
        return "Execute git commands. Use for version control operations."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Git command (e.g. 'status', 'diff', 'log --oneline -5')",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory (optional)",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str = "", workdir: str | None = None,
                      **kwargs: Any) -> str:
        cmd = f"git {command}"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=30, cwd=workdir or "."
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if result.returncode != 0:
                return f"Error: {err or 'git command failed'}"
            return out or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: git command timed out"
        except Exception as e:
            return f"Error: {e}"
