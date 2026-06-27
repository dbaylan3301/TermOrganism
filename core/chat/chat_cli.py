from __future__ import annotations

try:
    from core.chat.live_thinking import play_thinking_stream
except Exception:
    def play_thinking_stream(_thoughts):
        return


import asyncio
import os

import argparse

from .context import detect_context
from .executor import execute_plan
from .interpreter import interpret_message
from core.chat.semantic_interpreter import interpret_message as interpret_semantic_task
from core.chat.semantic_router import build_semantic_response
from .narrator import render_response
from .planner import build_plan
from .session import load_session, save_session, update_session
from .pause_layer import evaluate_reflective_pause
from core.context.intent_context import infer_intent_context
from core.watch.predictive_engine import predictive_whispers_for_target, record_predictive_repair_bridge, predictive_bridge_summary
from core.context.bridge_bias import choose_bridge_bias
from core.ui.animations import run_with_thinking, phases_for_goal, typewriter_effect
from rich.console import Console
from core.ui.theme import COLORS, STYLE


async def _render_with_typewriter(response: dict) -> None:
    console = Console()
    answer = str(response.get("answer", "")).strip()
    if not answer:
        return

    intent = str(response.get("intent", "-"))
    confidence = response.get("confidence", "-")
    ok = bool(response.get("ok"))

    console.print()
    status = f"[{STYLE['success']}]SUCCESS[/{STYLE['success']}]" if ok else f"[{STYLE['danger']}]FAILED[/{STYLE['danger']}]"
    console.print(f"[{STYLE['primary']}]TermOrganism[/{STYLE['primary']}] Chat  {status}")
    console.print(f"[{STYLE['accent']}]intent={intent}[/{STYLE['accent']}]  [{STYLE['info']}]confidence={confidence}[/{STYLE['info']}]")
    console.print()

    await typewriter_effect(answer, console_=console, char_delay=0.02, cursor_char="█")
    console.print()


async def process_message_async(message: str, *, session_id: str = "default") -> int:

    semantic_task = interpret_semantic_task(message)
    semantic_response = build_semantic_response(message, semantic_task, repo_root='.')
    if semantic_response is not None:
        semantic_response["message"] = message
        render_response(semantic_response)
        return 0

    session = load_session(session_id)
    intent = interpret_message(message, session)
    ctx = detect_context()
    intent_ctx = infer_intent_context(ctx)
    predictive_whispers = predictive_whispers_for_target(
        target_path=intent.target_hint,
        cwd=str(ctx.repo_root or ctx.cwd),
        focus=str(intent_ctx.get("focus", "general_runtime")),
        limit=4,
    )

    bridge_seed = predictive_bridge_summary(
        target_path=intent.target_hint,
        cwd=str(ctx.repo_root or ctx.cwd),
        focus=str(intent_ctx.get("focus", "general_runtime")),
        signature=None,
        limit=4,
    )
    bridge_bias = choose_bridge_bias(bridge_seed)

    plan = build_plan(intent, ctx, session, intent_ctx, predictive_whispers, bridge_bias)
    pause = evaluate_reflective_pause(intent, plan, ctx, session, intent_ctx, predictive_whispers)

    if pause.get("force_preview"):
        plan["preview_only"] = True
        plan["confirmation_required"] = True
        steps = list(plan.get("steps", []))
        marker = "reflective pause uygulandı; önce preview üretilecek"
        if marker not in steps:
            steps.insert(1, marker)
        plan["steps"] = steps
    response = await run_with_thinking(
        asyncio.to_thread(execute_plan, intent, plan, ctx, session),
        title="TermOrganism Thinking",
        phases=phases_for_goal(intent.goal),
    )

    response["message"] = message
    response["intent"] = intent.goal
    response["confidence"] = intent.confidence
    response["flags"] = intent.flags
    response["target_hint"] = intent.target_hint
    response["intent_context"] = intent_ctx
    response["reflective_pause"] = pause
    response["predictive_whispers"] = predictive_whispers
    response["bridge_bias"] = bridge_bias

    from core.llm.mimo_brain import generate_natural_response
    natural = generate_natural_response(
        user_message=message,
        context={"intent": intent.goal},
        intent=intent.goal,
        data=response,
    )
    if natural:
        response["answer"] = natural

    repair_obj = response.get("repair") or {}
    repair_result = repair_obj.get("result") if isinstance(repair_obj, dict) else None
    if isinstance(repair_result, dict):
        syn = repair_result.get("synaptic") or {}
        record_predictive_repair_bridge(
            target_path=intent.target_hint,
            cwd=str(ctx.repo_root or ctx.cwd),
            focus=str(intent_ctx.get("focus", "general_runtime")),
            signature=str(repair_result.get("signature", "repair:unknown")),
            route=str(repair_result.get("mode") or repair_result.get("strategy") or "-"),
            success=bool(repair_obj.get("ok")),
            predictive_whispers=predictive_whispers,
            synaptic_route=str(syn.get("route", "-")),
            synaptic_prior=float(syn.get("prior", 0.0) or 0.0),
            memory_matched=bool(syn.get("matched", False)),
        )
        response["predictive_repair_bridge"] = predictive_bridge_summary(
            target_path=intent.target_hint,
            cwd=str(ctx.repo_root or ctx.cwd),
            focus=str(intent_ctx.get("focus", "general_runtime")),
            signature=str(repair_result.get("signature", "repair:unknown")),
            limit=4,
        )

    update_session(
        session,
        goal=intent.goal,
        target_hint=intent.target_hint,
        response=response,
        flags=intent.flags,
    )
    save_session(session)

    thinking_items = []
    for step in response.get("plan", []):
        if str(step).strip():
            thinking_items.append(str(step).strip())
    if response.get("strategy_reason"):
        thinking_items.append(str(response.get("strategy_reason")).strip())
    if response.get("inference_reason"):
        thinking_items.append(str(response.get("inference_reason")).strip())

    if thinking_items:
        play_thinking_stream(thinking_items[:3])

    if os.getenv("TERMORGANISM_CHAT_TYPEWRITER", "0").strip().lower() in {"1", "true", "yes", "on"}:
        await _render_with_typewriter(response)
    else:
        render_response(response)
    return 0 if response.get("ok") else 1


async def repl_async(session_id: str = "default") -> int:
    console = Console()
    console.print(f"[{STYLE['primary']}]TermOrganism[/{STYLE['primary']}] Chat")
    console.print(f"[{STYLE['muted']}]Trading, kod onarımı, analiz... Çıkmak için: exit / quit[/{STYLE['muted']}]")
    while True:
        try:
            message = console.input(f"[{STYLE['primary']}]chat>[/{STYLE['primary']}] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not message:
            continue
        if message.lower() in {"exit", "quit", ":q"}:
            return 0
        await process_message_async(message, session_id=session_id)


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-chat")
    parser.add_argument("message", nargs="*", help="Doğal dil isteği")
    parser.add_argument("--session", default="default", help="Session kimliği")
    args = parser.parse_args()

    if args.message:
        return asyncio.run(process_message_async(" ".join(args.message), session_id=args.session))
    return asyncio.run(repl_async(session_id=args.session))


if __name__ == "__main__":
    raise SystemExit(main())
