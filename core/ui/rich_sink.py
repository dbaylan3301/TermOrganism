from __future__ import annotations

import time
from collections import deque
from pathlib import Path

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
            "Structure Scan": "🔎",
            "Syntax Recovery": "🧩",
            "Symbol Recovery": "🧠",
            "Intent Inference": "🧭",
            "Dependency Inference": "📦",
            "Initial Verification": "🧪",
            "Fallback Expert": "⇢",
            "Fallback Rewrite": "✍",
            "Final Verification": "✅",
            "Bundle Write": "🗂",
        }
        icon = icons.get(phase, "•")
        return f"[bold]{icon} {phase}[/bold]"

    def _render(self):
        root = Tree("[bold cyan]TermOrganism Thinking[/bold cyan]")
        for phase in self.phase_order:
            phase_node = root.add(self._phase_label(phase))
            events = list(self.phase_events.get(phase, []))
            for idx, event in enumerate(events):
                txt = self._event_text(event)
                if idx < len(events) - 1:
                    txt.stylize("dim")
                phase_node.add(txt)
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


class RichCinematicTreeThoughtSink(RichTreeThoughtSink):
    def __init__(self, max_phase_items: int = 6):
        super().__init__(max_phase_items=max_phase_items)

    def _style_for(self, kind: str) -> str:
        return {
            "info": "italic bright_black",
            "warn": "yellow",
            "success": "bold green",
            "fail": "bold red",
        }.get(kind, "white")

    def _pretty_path(self, path: str | None) -> str:
        if not path:
            return ""
        s = str(path)
        if "/demo/" in s:
            return "demo/" + s.split("/demo/", 1)[1]
        if "/tmp/termorganism_workspace_" in s:
            return s
        return Path(s).name

    def _extract_value(self, msg: str, key: str) -> str | None:
        token = f"{key}="
        if token not in msg:
            return None
        tail = msg.split(token, 1)[1]
        return tail.split()[0].strip()

    def _narrate(self, event: ThoughtEvent) -> str:
        phase = event.phase
        msg = event.message or ""

        if phase == "Input":
            path = self._extract_value(msg, "target") or event.file_path
            return f"tracking target: {self._pretty_path(path)}"

        if phase == "Reproduction":
            if "forced semantic mode" in msg:
                return "forced semantic mode active; runtime replay intentionally skipped"
            return msg

        if phase == "Localization":
            if msg.startswith("top="):
                top = self._extract_value(msg, "top")
                reason = self._extract_value(msg, "reason")
                if top:
                    if reason:
                        return f"top suspicion: {self._pretty_path(top)} • {reason.replace('_', ' ')}"
                    return f"top suspicion: {self._pretty_path(top)}"
            if msg.startswith("provider="):
                prov = self._extract_value(msg, "provider")
                return f"provider boundary: {self._pretty_path(prov)}"
            if msg.startswith("caller="):
                caller = self._extract_value(msg, "caller")
                return f"caller boundary: {self._pretty_path(caller)}"
            return msg

        if phase == "Expert Routing":
            if msg.startswith("experts="):
                return "consulting experts: " + msg.split("=", 1)[1]
            return msg

        if phase == "Hypothesis Generation":
            return msg

        if phase == "Candidate Generation":
            return msg

        if phase == "Planning":
            if "base_plans=" in msg and "multifile_plans=" in msg:
                b = self._extract_value(msg, "base_plans")
                m = self._extract_value(msg, "multifile_plans")
                return f"assembling repair plans: base={b} multifile={m}"
            return msg

        if phase == "Plan Expansion":
            if msg.startswith("total_plans="):
                return f"expanded to {msg.split('=', 1)[1]} candidate plans"
            return msg

        if phase == "Ranking":
            if "best strategy=" in msg:
                strategy = msg.split("best strategy=", 1)[1].split()[0]
                target = self._extract_value(msg, "target")
                return f"winner emerging: {strategy} @ {self._pretty_path(target)}"
            return msg

        if phase == "Plan Rejection":
            if "rejected=" in msg:
                rej = self._extract_value(msg, "rejected")
                return f"discarded {rej} weaker plans"
            return msg

        if phase == "Final Selection":
            if "strategy=" in msg:
                strategy = self._extract_value(msg, "strategy")
                target = self._extract_value(msg, "target")
                return f"winner locked: {strategy} @ {self._pretty_path(target)}"
            return msg

        if phase == "Sandbox Replay":
            applied = self._extract_value(msg, "applied_files")
            return f"replaying winner in isolated workspace ({applied or '0'} patched file(s))"

        if phase == "Sandbox":
            ok = self._extract_value(msg, "ok")
            rc = self._extract_value(msg, "returncode")
            return f"sandbox {'passed' if ok == 'True' else 'failed'} (returncode={rc})"

        if phase == "Contract Scoring":
            checks = self._extract_value(msg, "checks")
            return f"contract checks synthesized: {checks}"

        if phase == "Contract":
            ok = self._extract_value(msg, "ok")
            score = self._extract_value(msg, "score")
            return f"contract {'confirmed' if ok == 'True' else 'failed'} (score={score})"

        if phase == "Structure Scan":
            lines = self._extract_value(msg, "lines")
            imports = self._extract_value(msg, "imports")
            defs = self._extract_value(msg, "defs")
            classes = self._extract_value(msg, "classes")
            return f"scanning script surface: lines={lines} imports={imports} defs={defs} classes={classes}"

        if phase == "Syntax Recovery":
            changes = self._extract_value(msg, "changes")
            syntax_after = self._extract_value(msg, "syntax_error_after")
            if syntax_after == "False":
                return f"syntax frame stabilized; structural edits={changes}"
            return f"syntax still unstable after recovery; structural edits={changes}"

        if phase == "Symbol Recovery":
            changes = self._extract_value(msg, "changes")
            defs = self._extract_value(msg, "defs")
            classes = self._extract_value(msg, "classes")
            return f"rebuilding missing symbols: changes={changes} defs={defs} classes={classes}"

        if phase == "Intent Inference":
            summary = self._extract_value(msg, "summary")
            return f"inferred program intent: {summary}"

        if phase == "Dependency Inference":
            third_party = self._extract_value(msg, "third_party")
            unresolved = self._extract_value(msg, "unresolved")
            return f"dependency surface: third_party={third_party} unresolved={unresolved}"

        if phase == "Initial Verification":
            quality = self._extract_value(msg, "quality")
            overall = self._extract_value(msg, "overall_ok")
            return f"initial verification: quality={quality} overall_ok={overall}"

        if phase == "Fallback Expert":
            if "compile-only result detected" in msg:
                return "compile-only state detected; escalating to targeted repair expert"
            if "selected kind=" in msg:
                kind = self._extract_value(msg, "kind")
                target = self._extract_value(msg, "target")
                return f"fallback expert selected: {kind} @ {self._pretty_path(target)}"
            return msg

        if phase == "Fallback Rewrite":
            return "applied fallback source rewrite from winning repair candidate"

        if phase == "Final Verification":
            quality = self._extract_value(msg, "quality")
            overall = self._extract_value(msg, "overall_ok")
            return f"final verification: quality={quality} overall_ok={overall}"

        if phase == "Bundle Write":
            root = self._extract_value(msg, "bundle_root")
            return f"writing salvage bundle: {self._pretty_path(root)}"

        return msg

    def _delay_for(self, event: ThoughtEvent) -> float:
        return {
            "Input": 0.04,
            "Reproduction": 0.08,
            "Localization": 0.16,
            "Expert Routing": 0.10,
            "Hypothesis Generation": 0.11,
            "Candidate Generation": 0.08,
            "Planning": 0.10,
            "Plan Expansion": 0.10,
            "Ranking": 0.24,
            "Plan Rejection": 0.10,
            "Final Selection": 0.30,
            "Sandbox Replay": 0.12,
            "Sandbox": 0.16,
            "Contract Scoring": 0.10,
            "Contract": 0.22,
            "Apply": 0.12,
            "Structure Scan": 0.06,
            "Syntax Recovery": 0.12,
            "Symbol Recovery": 0.12,
            "Intent Inference": 0.08,
            "Dependency Inference": 0.08,
            "Initial Verification": 0.18,
            "Fallback Expert": 0.18,
            "Fallback Rewrite": 0.16,
            "Final Verification": 0.24,
            "Bundle Write": 0.08,
        }.get(event.phase, 0.06)

    def _event_text(self, event: ThoughtEvent) -> Text:
        rendered = self._narrate(event)
        parts: list[str] = [rendered]

        if event.confidence is not None and event.phase in {"Localization", "Ranking", "Final Selection"}:
            parts.append(f" (conf={event.confidence:.2f})")

        return Text("".join(parts), style=self._style_for(event.kind))

    def emit(self, event: ThoughtEvent) -> None:
        time.sleep(self._delay_for(event))
        super().emit(event)

    def _render(self):
        root = Tree("[bold cyan]TermOrganism Reasoning[/bold cyan]")
        for phase in self.phase_order:
            phase_node = root.add(self._phase_label(phase))
            events = list(self.phase_events.get(phase, []))
            for idx, event in enumerate(events):
                txt = self._event_text(event)
                if idx < len(events) - 1:
                    txt.stylize("dim")
                phase_node.add(txt)
        return Panel(root, title="TermOrganism Cinematic Reasoning", border_style="bright_blue")
