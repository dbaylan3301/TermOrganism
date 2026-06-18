from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class AgentContext:
    def __init__(self, cwd: str | None = None) -> None:
        self.cwd = cwd or os.getcwd()
        self.project_root = self._find_project_root()
        self.repo_info = self._get_repo_info()

    def _find_project_root(self) -> str:
        path = Path(self.cwd)
        for parent in [path] + list(path.parents):
            if (parent / ".git").exists():
                return str(parent)
            if (parent / "pyproject.toml").exists():
                return str(parent)
            if (parent / "package.json").exists():
                return str(parent)
        return self.cwd

    def _get_repo_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {"root": self.project_root}
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5, cwd=self.project_root
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()
        except Exception:
            pass
        return info

    def get_system_prompt(self) -> str:
        return f"""You are TermOrganism, an AI coding assistant. You help users with software engineering tasks.

Current working directory: {self.cwd}
Project root: {self.project_root}
Branch: {self.repo_info.get('branch', 'unknown')}

You have access to tools for:
- bash: Execute shell commands
- read: Read file contents
- write: Write files
- edit: Edit files with exact string replacement
- glob: Find files by pattern
- grep: Search file contents
- git: Git operations
- task: Manage tasks
- question: Ask the user
- memory: Store/search project memory

When you need to use a tool, respond with a tool call in this format:
```json
{{"tool": "tool_name", "args": {{"param": "value"}}}}
```

Be concise and direct. Write code that works. Don't explain obvious things."""
