from __future__ import annotations

import asyncio
import sys
from typing import Any

from .agent import Agent
from .ui import (
    print_banner, print_thinking, print_tool_call,
    print_tool_result, print_response, console, MIMO_COLORS
)


async def agent_callback(event: str, *args: Any) -> None:
    if event == "tool_start":
        print_tool_call(args[0], args[1])
    elif event == "tool_end":
        print_tool_result(args[0], args[1])
    elif event == "stream":
        pass


async def run_repl(provider: str | None = None) -> None:
    agent = Agent(provider_name=provider)
    print_banner()

    if console:
        console.print(f"  {MIMO_COLORS['muted']}Provider: {agent.provider.name()}{MIMO_COLORS['text']}")
        console.print(f"  {MIMO_COLORS['muted']}Type 'exit' or 'quit' to leave, 'clear' to reset session{MIMO_COLORS['text']}")
        console.print()

    while True:
        try:
            if console:
                prompt = f"  {MIMO_COLORS['primary']}termorg{MIMO_COLORS['text']} > "
            else:
                prompt = "termorg > "

            if sys.stdin.isatty():
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input(prompt)
                )
            else:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not user_input:
                    break
                user_input = user_input.strip()

        except (EOFError, KeyboardInterrupt):
            console.print(f"\n  {MIMO_COLORS['muted']}Hoşça kalın!{MIMO_COLORS['text']}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            if console:
                console.print(f"  {MIMO_COLORS['muted']}Hoşça kalın!{MIMO_COLORS['text']}")
            break

        if user_input.lower() == "clear":
            agent.clear_session()
            if console:
                console.print(f"  {MIMO_COLORS['muted']}Session temizlendi.{MIMO_COLORS['text']}")
            continue

        print_thinking()

        try:
            response = await agent.process_stream(user_input, callback=agent_callback)
            print_response(response)
        except Exception as e:
            if console:
                console.print(f"  {MIMO_COLORS['error']}Hata: {e}{MIMO_COLORS['text']}")
            else:
                print(f"Error: {e}")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="termorg", description="TermOrganism AI Assistant")
    parser.add_argument("--provider", choices=["groq", "openai", "anthropic", "ollama"], help="LLM provider")
    parser.add_argument("message", nargs="?", help="Single message mode")
    args = parser.parse_args()

    if args.message:
        async def single() -> None:
            agent = Agent(provider_name=args.provider)
            response = await agent.process_stream(args.message, callback=agent_callback)
            print_response(response)
        asyncio.run(single())
        return 0

    asyncio.run(run_repl(provider=args.provider))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
