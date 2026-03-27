from __future__ import annotations

from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from core.ui.thoughts import ThoughtEvent, ThoughtSink


class RichLiveThoughtSink(ThoughtSink):
    def __init__(self, max_lines: int = 14):
        self.console = Console()
        self.lines: deque[Text] = deque(maxlen=max_lines)
        self.live = Live(
            Panel(Text("waiting for events...", style="dim italic"), title="TermOrganism Thinking", border_style="blue"),
            console=self.console,
            refresh_per_second=8,
            transient=False,
            auto_refresh=False,
        )
        self.live.start()

    def _style_for(self, kind: str) -> str:
        return {
            "info": "dim italic grey70",
            "warn": "yellow",
            "success": "green",
            "fail": "bold red",
        }.get(kind, "dim")

    def emit(self, event: ThoughtEvent) -> None:
        parts: list[str] = [f"[{event.phase}] {event.message}"]

        if event.file_path:
            loc = event.file_path
            if event.line_no is not None:
                loc += f":{event.line_no}"
            parts.append(f" @ {loc}")

        if event.confidence is not None:
            parts.append(f" (conf={event.confidence:.2f})")

        line = Text("".join(parts), style=self._style_for(event.kind))
        self.lines.append(line)

        body = Group(*list(self.lines))
        self.live.update(
            Panel(
                body,
                title="TermOrganism Thinking",
                border_style="blue",
            ),
            refresh=True,
        )

    def close(self) -> None:
        try:
            self.live.stop()
        except Exception:
            pass
