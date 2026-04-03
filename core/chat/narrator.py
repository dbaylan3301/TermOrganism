from __future__ import annotations

from typing import Any

try:
    from rich import box
    from rich.columns import Columns
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    HAVE_RICH = True
except Exception:
    HAVE_RICH = False


def render_response(response: dict[str, Any]) -> None:
    if HAVE_RICH:
        _render_pretty(response)
    else:
        _render_plain(response)


def _render_plain(response: dict[str, Any]) -> None:
    print("TermOrganism Chat")
    print("-----------------")
    print(f"İstek: {response.get('message')}")
    print(f"Niyet: {response.get('intent')} (confidence={response.get('confidence')})")
    print("")
    print("Plan:")
    for i, step in enumerate(response.get("plan", []), start=1):
        print(f"{i}. {step}")
    print("")
    if response.get("command"):
        print(f"Komut: {response['command']}")
    if response.get("strategy_reason"):
        print(f"Strateji: {response['strategy_reason']}")
    if response.get("inference_reason"):
        print(f"Gerekçe: {response['inference_reason']}")
    print("")
    print("Sonuç:")
    print(response.get("answer", "-"))


def _render_pretty(response: dict[str, Any]) -> None:
    console = Console()

    ok = bool(response.get("ok"))
    intent = str(response.get("intent", "-"))
    confidence = response.get("confidence", "-")

    title = Text()
    title.append("TermOrganism Chat", style="bold magenta")
    title.append("  ")
    title.append("SUCCESS" if ok else "FAILED", style="bold green" if ok else "bold red")

    subtitle = Text()
    subtitle.append(f"intent={intent}", style="bright_cyan")
    subtitle.append("  ")
    subtitle.append(f"confidence={confidence}", style="bright_blue")

    header = Panel(
        Group(title, subtitle),
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    thinking_lines = []
    for i, step in enumerate(response.get("plan", []), start=1):
        thinking_lines.append(f"[bright_blue]{i}.[/] {step}")
    if response.get("strategy_reason"):
        thinking_lines.append("")
        thinking_lines.append(f"[rgb(210,175,120)]strategy[/]: {response['strategy_reason']}")
    if response.get("inference_reason"):
        thinking_lines.append(f"[rgb(210,175,120)]reason[/]: {response['inference_reason']}")
    if response.get("command"):
        thinking_lines.append(f"[grey70]command[/]: {response['command']}")

    thinking_panel = Panel(
        "\n".join(thinking_lines) if thinking_lines else "[grey62]no plan[/]",
        title="TermOrganism Thinking",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    ctx = response.get("context") or {}
    ctx_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
    ctx_table.add_column("k", style="grey62", width=16)
    ctx_table.add_column("v", style="white")
    ctx_table.add_row("cwd", str(ctx.get("cwd", "-")))
    ctx_table.add_row("repo_root", str(ctx.get("repo_root", "-")))
    ctx_table.add_row("branch", str(ctx.get("git_branch", "-")))
    ctx_table.add_row("repo_type", str(ctx.get("repo_type", "-")))
    ctx_table.add_row("target_hint", str(response.get("target_hint", "-")))
    context_panel = Panel(
        ctx_table,
        title="Context Snapshot",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    result_panel = Panel(
        str(response.get("answer", "-")),
        title="Result",
        border_style="rgb(110,90,180)",
        box=box.ROUNDED,
    )

    extra_panels = []

    pending = response.get("pending_action") or {}
    if pending:
        pending_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
        pending_table.add_column("k", style="grey62", width=16)
        pending_table.add_column("v", style="white")
        pending_table.add_row("kind", str(pending.get("kind", "-")))
        pending_table.add_row("target", str(pending.get("target", "-")))
        pending_table.add_row("risk", str(pending.get("risk", "-")))
        extra_panels.append(
            Panel(
                pending_table,
                title="Pending Action",
                border_style="rgb(110,90,180)",
                box=box.ROUNDED,
            )
        )

    repair = response.get("repair") or {}
    repair_result = repair.get("result") if isinstance(repair, dict) else None
    if isinstance(repair_result, dict):
        syn = repair_result.get("synaptic") or {}
        upd = repair_result.get("synaptic_memory_update") or {}
        rows = []
        if syn:
            rows.extend([
                ("memory", "matched" if syn.get("matched") else "cold"),
                ("route", str(syn.get("route", "-"))),
                ("prior", str(syn.get("prior", "-"))),
                ("seen", str(syn.get("seen_total", "-"))),
            ])
        if upd:
            rows.extend([
                ("learning", str(upd.get("delta", "-"))),
                ("weight", str(upd.get("error_route_weight", "-"))),
            ])
        if rows:
            mem_table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
            mem_table.add_column("k", style="grey62", width=16)
            mem_table.add_column("v", style="white")
            for k, v in rows:
                mem_table.add_row(k, v)
            extra_panels.append(
                Panel(
                    mem_table,
                    title="Synaptic Memory",
                    border_style="rgb(110,90,180)",
                    box=box.ROUNDED,
                )
            )

    console.print(header)
    console.print()
    console.print(Columns([thinking_panel, context_panel], expand=True, equal=True))
    console.print()
    console.print(result_panel)
    for panel in extra_panels:
        console.print()
        console.print(panel)
