from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class ProjectMemory:
    def __init__(self, project_dir: str | None = None) -> None:
        self._dir = Path(project_dir or Path.cwd()) / ".mimo" / "memory"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            self._index = json.loads(self._index_path.read_text(encoding="utf-8"))
        else:
            self._index = {"entries": {}}

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")

    def store(self, key: str, content: str, tags: list[str] | None = None) -> None:
        entry_path = self._dir / f"{key.replace('/', '_').replace(' ', '_')}.md"
        entry_path.write_text(content, encoding="utf-8")
        self._index["entries"][key] = {
            "path": str(entry_path),
            "ts": time.time(),
            "tags": tags or [],
        }
        self._save_index()

    def search(self, query: str) -> list[dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for key, meta in self._index.get("entries", {}).items():
            if query_lower in key.lower():
                path = Path(meta["path"])
                content = path.read_text(encoding="utf-8") if path.exists() else ""
                results.append({"key": key, "content": content, **meta})
        return results

    def get(self, key: str) -> str | None:
        meta = self._index.get("entries", {}).get(key)
        if not meta:
            return None
        path = Path(meta["path"])
        return path.read_text(encoding="utf-8") if path.exists() else None

    def list_all(self) -> list[dict[str, Any]]:
        results = []
        for key, meta in self._index.get("entries", {}).items():
            path = Path(meta["path"])
            content = path.read_text(encoding="utf-8")[:200] if path.exists() else ""
            results.append({"key": key, "content": content, **meta})
        return results

    def delete(self, key: str) -> bool:
        meta = self._index.get("entries", {}).get(key)
        if not meta:
            return False
        path = Path(meta["path"])
        if path.exists():
            path.unlink()
        del self._index["entries"][key]
        self._save_index()
        return True


_project_memory: ProjectMemory | None = None


def get_project_memory(project_dir: str | None = None) -> ProjectMemory:
    global _project_memory
    if _project_memory is None:
        _project_memory = ProjectMemory(project_dir)
    return _project_memory
