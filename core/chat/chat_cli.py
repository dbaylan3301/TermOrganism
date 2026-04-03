from __future__ import annotations

import argparse

from .context import detect_context
from .executor import execute_plan
from .interpreter import interpret_message
from .narrator import render_response
from .planner import build_plan
from .session import load_session, save_session, update_session


def process_message(message: str, *, session_id: str = "default") -> int:
    session = load_session(session_id)
    intent = interpret_message(message, session)
    ctx = detect_context()

    plan = build_plan(intent, ctx, session)
    response = execute_plan(intent, plan, ctx, session)

    response["message"] = message
    response["intent"] = intent.goal
    response["confidence"] = intent.confidence
    response["flags"] = intent.flags
    response["target_hint"] = intent.target_hint

    update_session(
        session,
        goal=intent.goal,
        target_hint=intent.target_hint,
        response=response,
        flags=intent.flags,
    )
    save_session(session)

    render_response(response)
    return 0 if response.get("ok") else 1


def repl(session_id: str = "default") -> int:
    print("TermOrganism Chat")
    print("Yaz ve devam et. Çıkmak için: exit / quit")
    while True:
        try:
            message = input("chat> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not message:
            continue
        if message.lower() in {"exit", "quit", ":q"}:
            return 0
        process_message(message, session_id=session_id)


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-chat")
    parser.add_argument("message", nargs="*", help="Doğal dil isteği")
    parser.add_argument("--session", default="default", help="Session kimliği")
    args = parser.parse_args()

    if args.message:
        return process_message(" ".join(args.message), session_id=args.session)
    return repl(session_id=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
