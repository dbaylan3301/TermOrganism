from __future__ import annotations

from collections import deque

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

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


class RichTreeThoughtSink(ThoughtSink):
    def __init__(self, max_phase_items: int = 6):
        self.console = Console()
        self.max_phase_items = max_phase_items
        self.phase_order: list[str] = []
        self.phase_events: dict[str, deque[ThoughtEvent]] = {}
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

    def _event_text(self, event: ThoughtEvent) -> Text:
        parts: list[str] = [event.message]

        if event.file_path:
            loc = event.file_path
            if event.line_no is not None:
                loc += f":{event.line_no}"
            parts.append(f" @ {loc}")

        if event.confidence is not None:
            parts.append(f" (conf={event.confidence:.2f})")

        return Text("".join(parts), style=self._style_for(event.kind))

    def _phase_label(self, phase: str) -> str:
        icons = {
            "Input": "⟡",
            "Reproduction": "⟳",
            "Localization": "⌁",
            "Expert Routing": "⇢",
            "Hypothesis Generation": "∴",
            "Candidate Generation": "⎇",
            "Planning": "⋯",
            "Plan Expansion": "⊞",
            "Ranking": "★",
            "Plan Rejection": "×",
            "Final Selection": "✔",
            "Sandbox Replay": "▣",
            "Sandbox": "🧪",
            "Contract Scoring": "∑",
            "Contract": "⚖",
            "Apply": "⬢",
        }
        icon = icons.get(phase, "•")
        return f"[bold]{icon} {phase}[/bold]"

    def _render(self):
        root = Tree("[bold cyan]TermOrganism Thinking[/bold cyan]")
        for phase in self.phase_order:
            phase_node = root.add(self._phase_label(phase))
            for event in self.phase_events.get(phase, []):
                phase_node.add(self._event_text(event))
        return Panel(root, title="TermOrganism Thinking", border_style="blue")

    def emit(self, event: ThoughtEvent) -> None:
        if event.phase not in self.phase_events:
            self.phase_events[event.phase] = deque(maxlen=self.max_phase_items)
            self.phase_order.append(event.phase)

        self.phase_events[event.phase].append(event)
        self.live.update(self._render(), refresh=True)

    def close(self) -> None:
        try:
            self.live.stop()
        except Exception:
            pass
