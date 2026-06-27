from __future__ import annotations

import sys
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.spinner import Spinner
    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False


if HAVE_RICH:
    console = Console()
else:
    console = None


from core.ui.theme import COLORS as MIMO_COLORS
MIMO_COLORS["error"] = MIMO_COLORS["danger"]


def print_banner() -> None:
    if not HAVE_RICH:
        print("TermOrganism AI (install rich for better UI)")
        return

    banner = Text()
    banner.append("  ╭─────────────────────────────────────────╮\n", style=MIMO_COLORS["primary"])
    banner.append("  │ ", style=MIMO_COLORS["primary"])
    banner.append("TermOrganism", style=f"bold {MIMO_COLORS['primary']}")
    banner.append(" AI", style=f"bold {MIMO_COLORS['accent']}")
    banner.append("                              │\n", style=MIMO_COLORS["primary"])
    banner.append("  │ ", style=MIMO_COLORS["primary"])
    banner.append("Merhaba! Ben TermOrganism.", style=MIMO_COLORS["text"])
    banner.append("              │\n", style=MIMO_COLORS["primary"])
    banner.append("  │ ", style=MIMO_COLORS["primary"])
    banner.append("Projen hakkında nasıl yardımcı          │\n", style=MIMO_COLORS["text"])
    banner.append("  │ ", style=MIMO_COLORS["primary"])
    banner.append("olabilirim?                             │\n", style=MIMO_COLORS["text"])
    banner.append("  ╰─────────────────────────────────────────╯", style=MIMO_COLORS["primary"])

    console.print(banner)
    console.print()


def print_thinking() -> None:
    if not HAVE_RICH:
        print("Thinking...")
        return
    console.print(f"  {MIMO_COLORS['muted']}Düşünüyorum...{MIMO_COLORS['text']}")


def print_tool_call(name: str, args: dict[str, Any]) -> None:
    if not HAVE_RICH:
        print(f"  Tool: {name}({args})")
        return

    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items() if k != "content")
    if len(args_str) > 100:
        args_str = args_str[:100] + "..."
    console.print(f"  {MIMO_COLORS['accent']}⚡ {name}{MIMO_COLORS['muted']}({args_str}){MIMO_COLORS['text']}")


def print_tool_result(name: str, result: str) -> None:
    if not HAVE_RICH:
        print(f"  Result: {result[:200]}")
        return

    lines = result.splitlines()
    preview = "\n".join(lines[:5])
    if len(lines) > 5:
        preview += f"\n  ... (+{len(lines)-5} lines)"
    if len(preview) > 300:
        preview = preview[:300] + "..."
    console.print(f"  {MIMO_COLORS['muted']}  └─ {preview}{MIMO_COLORS['text']}")


def print_response(text: str) -> None:
    if not HAVE_RICH:
        print(text)
        return

    console.print()
    try:
        console.print(Markdown(text))
    except Exception:
        console.print(text)
    console.print()


async def print_question(question: str, options: list[dict[str, Any]] | None = None) -> str:
    if not HAVE_RICH:
        print(question)
        if options:
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt['label']}: {opt.get('description', '')}")
        return input("Your answer: ")

    console.print(Panel(question, border_style=MIMO_COLORS["accent"], title="Soru"))

    if options:
        for i, opt in enumerate(options, 1):
            console.print(f"  {MIMO_COLORS['accent']}[{i}]{MIMO_COLORS['text']} {opt['label']} - {opt.get('description', '')}")

    console.print()
    return await _get_input("Cevabınız: ")


async def _get_input(prompt: str) -> str:
    if sys.stdin.isatty():
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: input(prompt))
            return result
        except (EOFError, KeyboardInterrupt):
            return ""
    return ""
