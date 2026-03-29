from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional


class RealWorkspacePool:
    """
    Measured scratch workspace pool for hot-force and fast-shortcut paths.
    """

    def __init__(self, size: int = 5):
        self.size = size
        self.available: asyncio.Queue[Path] = asyncio.Queue()
        self.root: Optional[Path] = None
        self.initialized = False
        self.stats = {"created": 0, "reused": 0, "missed": 0}

    async def initialize(self):
        if self.initialized:
            return

        self.root = Path(tempfile.mkdtemp(prefix="termorganism_pool_"))
        for i in range(self.size):
            ws = self.root / f"ws_{i:03d}"
            (ws / "work").mkdir(parents=True, exist_ok=True)
            await self.available.put(ws)
            self.stats["created"] += 1

        self.initialized = True
        print(f"Pool initialized: {self.size} workspaces ready")

    async def acquire(self) -> tuple[Path, dict]:
        start = time.monotonic()
        try:
            ws = await asyncio.wait_for(self.available.get(), timeout=0.05)
            self.stats["reused"] += 1
            latency_ms = (time.monotonic() - start) * 1000.0
            return ws, {
                "source": "pool",
                "latency_ms": round(latency_ms, 3),
                "id": ws.name,
            }
        except asyncio.TimeoutError:
            self.stats["missed"] += 1
            emergency = Path(tempfile.mkdtemp(prefix="termorganism_emergency_"))
            (emergency / "work").mkdir(parents=True, exist_ok=True)
            return emergency, {
                "source": "emergency",
                "latency_ms": 50.0,
                "id": emergency.name,
            }

    def release(self, ws: Path, dirty: bool = False):
        if "termorganism_emergency_" in ws.name:
            shutil.rmtree(ws, ignore_errors=True)
            return

        async def _return():
            work = ws / "work"
            if work.exists():
                for child in list(work.iterdir()):
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
            await self.available.put(ws)

        asyncio.create_task(_return())

    def get_stats(self) -> dict:
        total = self.stats["reused"] + self.stats["missed"]
        hit_rate = self.stats["reused"] / total if total > 0 else 0.0
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 4),
            "pool_size": self.size,
            "available_now": self.available.qsize(),
        }
