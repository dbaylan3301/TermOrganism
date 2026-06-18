from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class TaskTracker:
    def __init__(self, project_dir: str | None = None) -> None:
        self._dir = Path(project_dir or Path.cwd()) / ".mimo" / "tasks"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._load()

    def _load(self) -> None:
        if self._index_path.exists():
            self._data = json.loads(self._index_path.read_text(encoding="utf-8"))
        else:
            self._data = {"tasks": [], "next_id": 1}

    def _save(self) -> None:
        self._index_path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _next_id(self) -> str:
        tid = self._data["next_id"]
        self._data["next_id"] = tid + 1
        return f"T{tid}"

    def create(self, summary: str, notes: str | None = None) -> str:
        tid = self._next_id()
        task = {
            "id": tid,
            "summary": summary,
            "status": "todo",
            "notes": notes or "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._data["tasks"].append(task)
        self._save()
        return tid

    def list_all(self, status: str | None = None) -> list[dict[str, Any]]:
        tasks = self._data["tasks"]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks

    def get(self, task_id: str) -> dict[str, Any] | None:
        for t in self._data["tasks"]:
            if t["id"] == task_id:
                return t
        return None

    def update(self, task_id: str, status: str | None = None,
               summary: str | None = None, notes: str | None = None) -> bool:
        for t in self._data["tasks"]:
            if t["id"] == task_id:
                if status:
                    t["status"] = status
                if summary:
                    t["summary"] = summary
                if notes:
                    t["notes"] = notes
                t["updated_at"] = time.time()
                self._save()
                return True
        return False

    def delete(self, task_id: str) -> bool:
        for i, t in enumerate(self._data["tasks"]):
            if t["id"] == task_id:
                self._data["tasks"].pop(i)
                self._save()
                return True
        return False


_tracker: TaskTracker | None = None


def get_tracker(project_dir: str | None = None) -> TaskTracker:
    global _tracker
    if _tracker is None:
        _tracker = TaskTracker(project_dir)
    return _tracker
