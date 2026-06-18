from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from .signals import SignalResult

console = Console()

def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"

def display_signal(result: SignalResult):
    if result.signal == "NONE":
        console.print("[yellow]Sinyal bulunamadı[/yellow]")
        return

    color = "green" if result.signal == "LONG" else "red"
    emoji = "🟢" if result.signal == "LONG" else "🔴"

    header = f"{emoji} {result.signal} SİNYAL — {result.symbol}"

    lines = []
    lines.append(f"Giriş Fiyatı:  {format_price(result.entry_price)}")
    lines.append(f"SL:            {format_price(result.sl_price)}")
    lines.append(f"TP:            {format_price(result.tp_price)}")
    lines.append(f"Kaldıraç:      {result.leverage}x")
    lines.append(f"Risk/Kazanç:   1:{result.risk_reward:.2f}")

    lines.append("")
    lines.append("Koşullar:")
    for cond, met in result.conditions.items():
        check = "✓" if met else "✗"
        lines.append(f"  {check} {cond}")

    lines.append("")
    lines.append("İndikatörler:")
    for name, val in result.indicators.items():
        lines.append(f"  {name}: {val:.4f}")

    content = "\n".join(lines)

    panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style=color,
        box=box.DOUBLE,
    )
    console.print(panel)

def display_position(symbol: str, direction: str, entry: float,
                     current: float, sl: float, tp: float,
                     leverage: int, duration: str, pnl_pct: float):
    color = "green" if pnl_pct >= 0 else "red"
    pnl_sign = "+" if pnl_pct >= 0 else ""

    table = Table(show_header=False, box=box.SIMPLE_HEAVY)
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Pozisyon", f"[{color}]{direction} {symbol}[/{color}] {leverage}x")
    table.add_row("Giriş", format_price(entry))
    table.add_row("Güncel", format_price(current))
    table.add_row("P&L", f"[{color}]{pnl_sign}{pnl_pct:.2f}%[/{color}]")
    table.add_row("SL", format_price(sl))
    table.add_row("TP", format_price(tp))
    table.add_row("Süre", duration)

    console.print(table)

def display_exit_summary(symbol: str, direction: str, entry: float,
                        exit_price: float, pnl_pct: float, exit_type: str):
    color = "green" if pnl_pct >= 0 else "red"
    emoji = "✅" if pnl_pct >= 0 else "❌"

    panel = Panel(
        f"{emoji} Pozisyon Kapatıldı — {exit_type}\n\n"
        f"Symbol:    {symbol}\n"
        f"Yön:       {direction}\n"
        f"Giriş:     {format_price(entry)}\n"
        f"Çıkış:     {format_price(exit_price)}\n"
        f"P&L:       [{color}]{pnl_pct:+.2f}%[/{color}]",
        title="POZİSYON SONUÇ",
        border_style=color,
    )
    console.print(panel)
