from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path


class WorkspacePool:
    """
    Repo-safe pooled workspaces.
    This prepares the interface now; full planner/branch_executor wiring can come later.
    """

    def __init__(self, size: int = 5):
        self.size = size
        self.available: asyncio.Queue[Path] = asyncio.Queue()
        self.template_dir = Path(".termorganism/workspace_template")
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        self.template_dir.mkdir(parents=True, exist_ok=True)
        for _ in range(self.size):
            ws = self._create_workspace()
            await self.available.put(ws)
        self._initialized = True

    def _create_workspace(self) -> Path:
        ws = Path(tempfile.mkdtemp(prefix="termorganism_ws_"))
        (ws / "env").mkdir(parents=True, exist_ok=True)

        if self.template_dir.exists():
            for item in self.template_dir.iterdir():
                target = ws / "env" / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
        return ws

    async def acquire(self) -> Path:
        await self.initialize()
        try:
            return await asyncio.wait_for(self.available.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return self._create_workspace()

    def release(self, ws: Path, dirty: bool = False):
        if dirty:
            asyncio.create_task(self._reset_workspace(ws))
        asyncio.create_task(self.available.put(ws))

    async def _reset_workspace(self, ws: Path):
        env = ws / "env"
        if env.exists():
            shutil.rmtree(env, ignore_errors=True)
        env.mkdir(parents=True, exist_ok=True)
        if self.template_dir.exists():
            for item in self.template_dir.iterdir():
                target = env / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
