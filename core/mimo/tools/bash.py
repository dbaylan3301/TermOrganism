from __future__ import annotations

import asyncio
from typing import Any

from . import Tool


class BashTool(Tool):
    def name(self) -> str:
        return "bash"

    def description(self) -> str:
        return "Execute a bash command. Use for system operations, running scripts, git, npm, etc."

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory (optional)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120)",
                    "default": 120,
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str = "", workdir: str | None = None,
                      timeout: int = 120, **kwargs: Any) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            out = stdout.decode(errors="replace").strip()
            err = stderr.decode(errors="replace").strip()
            result = ""
            if out:
                result += out
            if err:
                result += f"\n[stderr]\n{err}" if result else err
            if proc.returncode != 0:
                result += f"\n[exit code: {proc.returncode}]"
            return result or "(no output)"
        except asyncio.TimeoutError:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"
