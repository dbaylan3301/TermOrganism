from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SessionMemory:
    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []
        self._context: dict[str, Any] = {}

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        self._messages.append({"role": role, "content": content, "ts": time.time(), **kwargs})

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def clear(self) -> None:
        self._messages.clear()
        self._context.clear()
