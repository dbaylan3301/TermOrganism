from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class HookEvent:
    name: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
