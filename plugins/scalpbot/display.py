from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.align import Align
from .signals import SignalResult
import time

console = Console()

# MiMoCode Color Theme
COLORS = {
    "primary": "#00D4AA",      # Teal/Cyan
    "secondary": "#7C3AED",    # Purple
    "accent": "#F59E0B",       # Amber
    "success": "#10B981",      # Green
    "danger": "#EF4444",       # Red
    "warning": "#F97316",      # Orange
    "muted": "#6B7280",        # Gray
    "bg": "#1E293B",           # Dark Blue
    "text": "#F8FAFC",         # Light
    "border": "#334155",       # Border Gray
}

def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"

def get_pnl_color(pnl: float) -> str:
    if pnl >= 5:
        return "#10B981"
    elif pnl >= 0:
        return "#34D399"
    elif pnl > -5:
        return "#F87171"
    else:
        return "#EF4444"

def display_banner():
    """Display MiMoCode styled banner."""
    banner = """
[bold #00D4AA]╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ███╗ ██████╗ ██████╗  ██████╗ ██╗   ██╗████████╗   ║
║   ████╗ ████║██╔═══██╗██╔══██╗██╔═══██╗██║   ██║╚══██╔══╝   ║
║   ██╔████╔██║██║   ██║██║  ██║██║   ██║██║   ██║   ██║      ║
║   ██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║   ██║   ██║      ║
║   ██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝╚██████╔╝   ██║      ║
║   ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝    ╚═╝      ║
║                                                              ║
║          [bold #7C3AED]5x SCALP BOT[/bold #7C3AED] • Crypto Futures Signal Engine           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝[/bold #00D4AA]"""
    console.print(Align.center(banner))

def display_scanning_header():
    """Display scanning status header."""
    console.print()
    console.print(Panel(
        f"[bold #00D4AA]⚡ TARAMA BAŞLATILDI[/bold #00D4AA]\n"
        f"[#6B7280]   Mod: Akıllı Filtreleme • Veri: Yahoo Finance Canlı[/#6B7280]\n"
        f"[#6B7280]   {time.strftime('%H:%M:%S')} UTC[/#6B7280]",
        border_style="#334155",
        box=box.ROUNDED,
        padding=(0, 2)
    ))

def display_screening_results(screened: list):
    """Display screening results in MiMoCode style."""
    if not screened:
        return

    table = Table(
        title="[bold #00D4AA]📊 ANALİZ SONUÇLARI[/bold #00D4AA]",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold #7C3AED",
        border_style="#334155",
        title_style="bold #00D4AA"
    )

    table.add_column("#", style="#6B7280", width=3)
    table.add_column("COIN", style="bold #F8FAFC", width=8)
    table.add_column("SKOR", style="bold #F59E0B", width=6)
    table.add_column("RSI", width=6)
    table.add_column("ATR%", width=8)
    table.add_column("VOL", width=8)
    table.add_column("SEBEP", style="#6B7280", no_wrap=True)

    for i, coin in enumerate(screened[:5], 1):
        rsi_color = "#10B981" if 40 <= coin.get("rsi", 50) <= 60 else "#F97316"
        score_color = "#10B981" if coin["score"] >= 70 else "#F59E0B" if coin["score"] >= 50 else "#6B7280"

        table.add_row(
            str(i),
            f"[bold]{coin['symbol']}[/bold]",
            f"[{score_color}]{coin['score']}[/{score_color}]",
            f"[{rsi_color}]{coin.get('rsi', 0):.0f}[/{rsi_color}]",
            f"{coin.get('atr_pct', 0):.3f}%",
            f"{coin.get('vol_ratio', 0):.1f}x",
            coin["reasons"][0] if coin["reasons"] else "-"
        )

    console.print(table)

def display_signal(result: SignalResult):
    """Display signal in MiMoCode professional style."""
    if result.signal == "NONE":
        return

    is_long = result.signal == "LONG"
    color = "#10B981" if is_long else "#EF4444"
    emoji = "▲" if is_long else "▼"
    direction_text = "LONG" if is_long else "SHORT"

    # Header with ASCII art
    header = f"""
[bold {color}]┌─────────────────────────────────────────────────────────────┐
│  {emoji} {result.signal} SİNYAL • {result.symbol}                              │
│  [{time.strftime('%Y-%m-%d %H:%M:%S UTC')}]                               │
└─────────────────────────────────────────────────────────────┘[/bold {color}]"""

    # Main info table
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Key", style="#6B7280", width=14)
    info_table.add_column("Value", style="bold #F8FAFC")

    info_table.add_row("Giriş Fiyatı", f"[bold {color}]{format_price(result.entry_price)}[/bold {color}]")
    info_table.add_row("Stop Loss", f"[#EF4444]{format_price(result.sl_price)}[/#EF4444]")
    info_table.add_row("Take Profit", f"[#10B981]{format_price(result.tp_price)}[/#10B981]")
    info_table.add_row("Kaldıraç", f"[#F59E0B]{result.leverage}x[/#F59E0B]")
    info_table.add_row("Risk/Kazanç", f"[bold #7C3AED]1:{result.risk_reward:.2f}[/bold #7C3AED]")

    # Risk calculation
    risk_pct = abs(result.entry_price - result.sl_price) / result.entry_price * 100 * result.leverage
    reward_pct = abs(result.tp_price - result.entry_price) / result.entry_price * 100 * result.leverage
    info_table.add_row("Potansiyel K/Z", f"[#10B981]+{reward_pct:.1f}%[/#10B981] / [#EF4444]-{risk_pct:.1f}%[/#EF4444]")

    # Conditions
    cond_lines = []
    for cond, met in result.conditions.items():
        icon = "[#10B981]✓[/#10B981]" if met else "[#EF4444]✗[/#EF4444]"
        cond_lines.append(f"  {icon} {cond}")

    # Indicators
    ind_lines = []
    for name, val in result.indicators.items():
        ind_lines.append(f"  [:#6B7280]{name}[/:#6B7280]: {val:.4f}")

    content = Text.assemble(
        info_table,
        "\n",
        "[bold #7C3AED]━━━ Koşullar ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #7C3AED]\n",
        "\n".join(cond_lines),
        "\n",
        "[bold #7C3AED]━━━ İndikatörler ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #7C3AED]\n",
        "\n".join(ind_lines),
        "\n",
        f"\n[bold #F59E0B]📌 Komut:[/bold #F59E0B] [:#F8FAFC]pozisyon_al {result.symbol} {result.signal} {format_price(result.entry_price)}[/:#F8FAFC]"
    )

    panel = Panel(
        Align.left(content),
        title=header,
        title_align="left",
        border_style=color,
        box=box.DOUBLE,
        padding=(1, 2)
    )
    console.print(panel)
    console.print()

def display_position(symbol: str, direction: str, entry: float,
                     current: float, sl: float, tp: float,
                     leverage: int, duration: str, pnl_pct: float):
    """Display live position tracking in MiMoCode style."""
    color = get_pnl_color(pnl_pct)
    pnl_sign = "+" if pnl_pct >= 0 else ""
    is_profit = pnl_pct >= 0

    # Progress bar
    total_range = abs(tp - sl) if direction == "LONG" else abs(sl - tp)
    if direction == "LONG":
        current_pos = (current - sl) / total_range * 100
    else:
        current_pos = (sl - current) / total_range * 100

    bar_length = 30
    filled = int(current_pos / 100 * bar_length)
    bar = "█" * max(0, filled) + "░" * max(0, bar_length - filled)

    table = Table(
        title=f"[bold {color}]{'▲' if is_profit else '▼'} POZİSYON AÇIK • {symbol} {direction} {leverage}x[/bold {color}]",
        box=box.ROUNDED,
        border_style=color,
        title_style=f"bold {color}"
    )

    table.add_column("Metrik", style="#6B7280", width=12)
    table.add_column("Değer", style="bold #F8FAFC", width=20)

    table.add_row("Giriş", format_price(entry))
    table.add_row("Güncel", f"[bold {color}]{format_price(current)}[/bold {color}]")
    table.add_row("P&L", f"[bold {color}]{pnl_sign}{pnl_pct:.2f}%[/bold {color}]")
    table.add_row("SL", f"[#EF4444]{format_price(sl)}[/#EF4444]")
    table.add_row("TP", f"[#10B981]{format_price(tp)}[/#10B981]")
    table.add_row("Süre", f"[#F59E0B]{duration}[/#F59E0B]")
    table.add_row("İlerleme", f"[{color}]{bar}[/{color}] {current_pos:.1f}%")

    console.print(table)

def display_exit_summary(symbol: str, direction: str, entry: float,
                        exit_price: float, pnl_pct: float, exit_type: str):
    """Display exit summary in MiMoCode style."""
    is_profit = pnl_pct >= 0
    color = "#10B981" if is_profit else "#EF4444"
    emoji = "✓" if is_profit else "✗"
    result_text = "KAZANÇ" if is_profit else "ZARAR"

    header = f"""
[bold {color}]╔═══════════════════════════════════════════════════════════════╗
║  {emoji} POZİSYON KAPATILDI • {result_text}                            ║
╚═══════════════════════════════════════════════════════════════╝[/bold {color}]"""

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="#6B7280", width=14)
    table.add_column("Value", style="bold #F8FAFC")

    table.add_row("Symbol", f"[bold]{symbol}[/bold]")
    table.add_row("Yön", f"[bold {color}]{direction}[/bold {color}]")
    table.add_row("Giriş", format_price(entry))
    table.add_row("Çıkış", f"[bold {color}]{format_price(exit_price)}[/bold {color}]")
    table.add_row("P&L", f"[bold {color}]{pnl_pct:+.2f}%[/bold {color}]")
    table.add_row("Çıkış Tipi", f"[#F59E0B]{exit_type}[/#F59E0B]")

    panel = Panel(
        Align.center(table),
        title=header,
        title_align="center",
        border_style=color,
        box=box.HEAVY,
        padding=(1, 3)
    )
    console.print(panel)

def display_status_bar(signal_count: int, scan_time: float):
    """Display status bar at bottom."""
    console.print()
    console.print(Panel(
        f"[#6B7280]⚡ Tarama: {scan_time:.1f}s • "
        f"📊 Sinyaller: {signal_count} • "
        f"🕐 {time.strftime('%H:%M:%S')} UTC[/#6B7280]",
        border_style="#334155",
        box=box.ROUNDED,
        padding=(0, 1)
    ))
