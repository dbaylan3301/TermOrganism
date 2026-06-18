from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GlobalMemory:
    def __init__(self) -> None:
        self._path = Path.home() / ".termorganism" / "memory" / "global.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        else:
            self._data = {"preferences": {}, "learnings": []}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._data.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        self._data.setdefault("preferences", {})[key] = value
        self._save()

    def add_learning(self, content: str) -> None:
        self._data.setdefault("learnings", []).append({"content": content})
        self._save()

    def get_learnings(self) -> list[dict[str, Any]]:
        return self._data.get("learnings", [])


_global_memory: GlobalMemory | None = None


def get_global_memory() -> GlobalMemory:
    global _global_memory
    if _global_memory is None:
        _global_memory = GlobalMemory()
    return _global_memory
