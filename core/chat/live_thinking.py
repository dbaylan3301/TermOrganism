from __future__ import annotations

import os
import time
from collections import deque

try:
    from rich import box
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
    HAVE_RICH = True
except Exception:
    HAVE_RICH = False


def _enabled() -> bool:
    raw = str(os.getenv("TERMORGANISM_CHAT_CINEMATIC", "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _speed() -> float:
    try:
        return float(os.getenv("TERMORGANISM_CHAT_CINEMATIC_SPEED", "0.18"))
    except Exception:
        return 0.18


def _max_lines() -> int:
    try:
        return max(2, int(os.getenv("TERMORGANISM_CHAT_CINEMATIC_LINES", "3")))
    except Exception:
        return 3


def _render_frame(lines: list[str]) -> Panel:
    text = Text()
    total = len(lines)
    for i, line in enumerate(lines):
        if not str(line).strip():
            continue
        age = total - i
        if age >= 3:
            style = "grey35 italic"
        elif age == 2:
            style = "grey50 italic"
        else:
            style = "grey78"
        text.append("• ", style=style)
        text.append(str(line).strip(), style=style)
        text.append("\n")

    if not lines:
        text.append("• düşünüyorum...", style="grey50 italic")

    return Panel(
        Group(text),
        title="TermOrganism Thinking",
        border_style="rgb(90,90,120)",
        box=box.ROUNDED,
    )


def play_thinking_stream(thoughts: list[str]) -> None:
    if not _enabled() or not HAVE_RICH:
        return

    items = [str(x).strip() for x in thoughts if str(x).strip()][:3]
    if not items:
        return

    console = Console()
    window = deque(maxlen=_max_lines())

    with Live(_render_frame([]), console=console, refresh_per_second=12, transient=True) as live:
        for item in items:
            window.append(item)
            live.update(_render_frame(list(window)))
            time.sleep(_speed())
