from __future__ import annotations

from typing import Any

from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class PrettyTheme:
    title = "bold magenta"
    dim = "grey62"
    ok = "bold green"
    err = "bold red"
    accent = "bright_cyan"
    info = "bright_blue"
    panel = "rgb(110,90,180)"


def _status_style(success: bool) -> str:
    return PrettyTheme.ok if success else PrettyTheme.err


def _status_label(success: bool) -> str:
    return "SUCCESS" if success else "FAILED"


def _table_panel(title: str, rows: list[tuple[str, str]]) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
    table.add_column("k", style=PrettyTheme.dim, width=18)
    table.add_column("v", style="white")
    for k, v in rows:
        table.add_row(k, v)
    return Panel(table, title=title, border_style=PrettyTheme.panel, box=box.ROUNDED)


def _activity_panel(payload: dict[str, Any]) -> Panel:
    lines: list[str] = []
    routing = payload.get("routing") or {}
    if routing:
        lines.append(
            f"[{PrettyTheme.accent}]routing[/]: "
            f"{routing.get('requested_mode', '?')} → {routing.get('effective_mode', '?')}"
        )
        reason = routing.get("planner_reason")
        if reason:
            lines.append(f"[{PrettyTheme.dim}]reason[/]: {reason}")

    for agent in payload.get("agent_results", [])[:8]:
        name = str(agent.get("agent", "?"))
        ok = bool(agent.get("ok"))
        mark = "✓" if ok else "✗"
        style = PrettyTheme.ok if ok else PrettyTheme.err
        lines.append(f"[{style}]{mark}[/] {name}")

    before_hooks = payload.get("before_repair_hooks") or []
    after_hooks = payload.get("after_verify_hooks") or []
    if before_hooks or after_hooks:
        lines.append(f"[{PrettyTheme.info}]hooks[/]: before={len(before_hooks)} after={len(after_hooks)}")

    if not lines:
        lines.append("[grey62]no activity[/]")

    return Panel("\n".join(lines), title="Recent Activity", border_style=PrettyTheme.panel, box=box.ROUNDED)


def _checks_panel(payload: dict[str, Any]) -> Panel:
    checks = payload.get("required_checks") or []
    body = "[grey62]No required checks[/]" if not checks else "\n".join(f"• {item}" for item in checks)
    return Panel(body, title="Required Checks", border_style=PrettyTheme.panel, box=box.ROUNDED)


def _header(payload: dict[str, Any]) -> Panel:
    success = bool(payload.get("success"))
    mode = str(payload.get("mode") or "?")
    signature = str(payload.get("signature") or "-")
    daemon = payload.get("daemon") or {}
    socket_path = str(daemon.get("socket") or "-")

    title = Text()
    title.append("TermOrganism", style=PrettyTheme.title)
    title.append("  ")
    title.append(_status_label(success), style=_status_style(success))

    meta = Text()
    meta.append(f"mode={mode}", style=PrettyTheme.accent)
    meta.append("  ")
    meta.append(f"signature={signature}", style=PrettyTheme.info)
    meta.append("  ")
    meta.append(f"daemon={socket_path}", style=PrettyTheme.dim)

    return Panel(Group(title, meta), border_style=PrettyTheme.panel, box=box.ROUNDED)


def render_pretty(payload: dict[str, Any]) -> None:
    success = bool(payload.get("success"))
    confidence = payload.get("confidence") or {}
    verify = payload.get("verify") or {}
    pool = payload.get("workspace_pool") or {}

    summary = _table_panel(
        "Repair State",
        [
            ("target", str(payload.get("target_file") or "-")),
            ("mode", str(payload.get("mode") or "-")),
            ("strategy", str(payload.get("strategy") or "-")),
            ("confidence", str(confidence.get("score", "-"))),
            ("verify.ok", str(verify.get("ok", "-"))),
            ("workspace", str(pool.get("id") or "-")),
        ],
    )

    console.print(_header(payload))
    console.print()
    console.print(Columns([summary, _activity_panel(payload)], expand=True, equal=True))
    console.print()
    console.print(_checks_panel(payload))

    if not success and payload.get("error"):
        console.print()
        console.print(Panel(str(payload["error"]), title="Error", border_style=PrettyTheme.err, box=box.ROUNDED))
