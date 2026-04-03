from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import time


@dataclass(slots=True)
class ChatSessionState:
    session_id: str = "default"
    last_goal: str | None = None
    last_target: str | None = None
    last_command: str | None = None
    last_result: str | None = None
    last_timeout: bool = False
    user_mode: dict[str, bool] = field(default_factory=dict)
    pending_action: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    updated_at: float = 0.0


def _session_path(session_id: str) -> Path:
    base = Path.home() / ".termorganism" / "chat_sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{session_id}.json"


def load_session(session_id: str = "default") -> ChatSessionState:
    path = _session_path(session_id)
    if not path.exists():
        return ChatSessionState(session_id=session_id)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ChatSessionState(session_id=session_id)

    return ChatSessionState(
        session_id=str(data.get("session_id", session_id)),
        last_goal=data.get("last_goal"),
        last_target=data.get("last_target"),
        last_command=data.get("last_command"),
        last_result=data.get("last_result"),
        last_timeout=bool(data.get("last_timeout", False)),
        user_mode=dict(data.get("user_mode") or {}),
        pending_action=dict(data.get("pending_action") or {}),
        notes=list(data.get("notes") or []),
        updated_at=float(data.get("updated_at", 0.0) or 0.0),
    )


def save_session(state: ChatSessionState) -> None:
    state.updated_at = time.time()
    path = _session_path(state.session_id)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def update_session(
    state: ChatSessionState,
    *,
    goal: str,
    target_hint: str | None,
    response: dict[str, Any],
    flags: dict[str, bool] | None = None,
) -> None:
    state.last_goal = goal
    if target_hint:
        state.last_target = target_hint
    elif response.get("target_hint"):
        state.last_target = str(response["target_hint"])

    if response.get("command"):
        state.last_command = str(response["command"])

    if response.get("timed_out"):
        state.last_result = "timeout"
    elif response.get("preview_only"):
        state.last_result = "preview"
    else:
        state.last_result = "ok" if response.get("ok") else "failed"

    state.last_timeout = bool(response.get("timed_out", False))

    if flags:
        merged = dict(state.user_mode)
        merged.update(flags)
        state.user_mode = merged

    if response.get("clear_pending"):
        state.pending_action = {}
    elif response.get("pending_action"):
        state.pending_action = dict(response["pending_action"])

    note = response.get("session_note")
    if note:
        state.notes = [str(note)] + state.notes[:9]
