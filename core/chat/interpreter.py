from __future__ import annotations

from dataclasses import dataclass, field

from .intent import classify_intent
from .session import ChatSessionState


@dataclass(slots=True)
class ChatIntent:
    goal: str
    confidence: float
    target_hint: str | None = None
    flags: dict[str, bool] = field(default_factory=dict)
    follow_up: bool = False
    raw_intent: str | None = None


_CONFIRM_WORDS = {"tamam", "uygula", "devam", "onay", "evet", "go", "tamam uygula"}
_CANCEL_WORDS = {"iptal", "vazgeç", "hayır", "dur", "stop"}
_NARROW_TEST_WORDS = {
    "daha dar koş", "dar koş", "dar test", "tek test", "tek dosya", "ilk fail", "-k", "daralt"
}


def _has_any(text: str, words: set[str]) -> bool:
    padded = f" {text.strip()} "
    return any(f" {word} " in padded for word in words)


def interpret_message(message: str, session: ChatSessionState) -> ChatIntent:
    raw = message.strip()
    lowered = raw.lower()

    if session.pending_action and (_has_any(lowered, _CONFIRM_WORDS) or lowered in _CONFIRM_WORDS):
        return ChatIntent(
            goal="confirm_pending",
            confidence=0.97,
            target_hint=session.pending_action.get("target"),
            flags=dict(session.user_mode),
            follow_up=True,
            raw_intent="confirm_pending",
        )

    if session.pending_action and (_has_any(lowered, _CANCEL_WORDS) or lowered in _CANCEL_WORDS):
        return ChatIntent(
            goal="cancel_pending",
            confidence=0.97,
            target_hint=session.pending_action.get("target"),
            flags=dict(session.user_mode),
            follow_up=True,
            raw_intent="cancel_pending",
        )

    if session.last_goal in {"run_tests", "run_tests_narrow"} and any(w in lowered for w in _NARROW_TEST_WORDS):
        return ChatIntent(
            goal="run_tests_narrow",
            confidence=0.92,
            target_hint=session.last_target,
            flags=dict(session.user_mode),
            follow_up=True,
            raw_intent="run_tests_narrow",
        )

    base = classify_intent(raw)
    if base.target_hint:
        target_hint = base.target_hint
    elif base.intent in {"repair", "diagnose", "run_tests_narrow"}:
        target_hint = session.last_target
    else:
        target_hint = None

    flags = dict(base.flags)
    if "önce açıkla" in lowered or "önce anlat" in lowered or "önce söyle" in lowered:
        flags["explain"] = True
    if "onay verince" in lowered or "ben onay verince" in lowered:
        flags["explain"] = True
    if "direkt yap" in lowered or "hemen uygula" in lowered:
        flags["auto"] = True

    goal = base.intent
    return ChatIntent(
        goal=goal,
        confidence=base.confidence,
        target_hint=target_hint,
        flags=flags,
        follow_up=False,
        raw_intent=base.intent,
    )
