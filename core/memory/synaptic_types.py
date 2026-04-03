from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SynapticNode:
    id: str
    type: str
    label: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SynapticEdge:
    source_id: str
    target_id: str
    kind: str
    weight: float = 0.50
    success_count: int = 0
    failure_count: int = 0
    seen_count: int = 0
    last_seen_ts: float = 0.0
    avg_confidence: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SynapticEvent:
    event_type: str
    payload: dict[str, Any]
    ts: float = 0.0
