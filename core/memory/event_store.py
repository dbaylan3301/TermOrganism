from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVENTS_PATH = Path("memory/TermOrganism/repair_events.jsonl")

def _ensure_path() -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not EVENTS_PATH.exists():
        EVENTS_PATH.touch()

def append_event(payload: dict[str, Any]) -> None:
    _ensure_path()
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

def store_event(payload: dict[str, Any]) -> None:
    append_event(payload)

def write_event(payload: dict[str, Any]) -> None:
    append_event(payload)

def read_events(limit: int | None = None) -> list[dict[str, Any]]:
    _ensure_path()
    lines = EVENTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    if limit is not None:
        lines = lines[-limit:]

    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"_raw": line, "_parse_error": True})
    return out

class EventStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else EVENTS_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append_event(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

    def store_event(self, payload: dict[str, Any]) -> None:
        self.append_event(payload)

    def write_event(self, payload: dict[str, Any]) -> None:
        self.append_event(payload)

    def read_events(self, limit: int | None = None) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        if limit is not None:
            lines = lines[-limit:]

        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                out.append({"_raw": line, "_parse_error": True})
        return out
