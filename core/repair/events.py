from __future__ import annotations

from typing import Any

from core.ui.thoughts import ThoughtEvent
from core.memory import event_store


def emit_thought(
    thought_bus: Any,
    phase: str,
    message: str,
    *,
    kind: str = "info",
    confidence: float | None = None,
    file_path: str | None = None,
    line_no: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if thought_bus is None:
        return
    try:
        thought_bus.emit(
            ThoughtEvent(
                phase=phase,
                message=message,
                kind=kind,
                confidence=confidence,
                file_path=file_path,
                line_no=line_no,
                meta=meta or {},
            )
        )
    except Exception:
        pass


class EventStoreAdapter:
    def append_event(self, payload: dict[str, Any]) -> None:
        if hasattr(event_store, "append_event"):
            event_store.append_event(payload)
            return
        if hasattr(event_store, "store_event"):
            event_store.store_event(payload)
            return
        if hasattr(event_store, "write_event"):
            event_store.write_event(payload)
            return
