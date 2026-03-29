from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from core.hooks.events import HookEvent
from core.hooks.runner import run_hook


class HookEngine:
    def __init__(self) -> None:
        self._hooks: dict[str, list[str]] = defaultdict(list)

    def register(self, event_name: str, command: str | Path) -> None:
        self._hooks[event_name].append(str(command))

    def dispatch(self, event: HookEvent) -> list[dict]:
        results = []
        for command in self._hooks.get(event.name, []):
            results.append(run_hook(command, event))
        return results
