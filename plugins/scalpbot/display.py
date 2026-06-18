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

COLORS = {
    "primary": "#00D4AA",
    "secondary": "#7C3AED",
    "accent": "#F59E0B",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F97316",
    "muted": "#6B7280",
    "text": "#F8FAFC",
    "border": "#334155",
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

def get_confidence_color(confidence: float) -> str:
    if confidence >= 85:
        return "#10B981"
    elif confidence >= 70:
        return "#34D399"
    elif confidence >= 50:
        return "#F59E0B"
    else:
        return "#EF4444"

def get_confidence_bar(confidence: float) -> str:
    bar_length = 20
    filled = int(confidence / 100 * bar_length)
    color = get_confidence_color(confidence)
    return f"[{color}]{'█' * filled}{'░' * (bar_length - filled)}[/{color}]"

def display_banner():
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
    table.add_column("PATTERN", style="#7C3AED", width=10)
    table.add_column("SEBEP", style="#6B7280", no_wrap=True)

    for i, coin in enumerate(screened[:5], 1):
        rsi_color = "#10B981" if 40 <= coin.get("rsi", 50) <= 60 else "#F97316"
        score_color = "#10B981" if coin["score"] >= 70 else "#F59E0B" if coin["score"] >= 50 else "#6B7280"
        patterns = coin.get("patterns", [])
        pattern_str = ", ".join(patterns[:2]) if patterns else "-"

        table.add_row(
            str(i),
            f"[bold]{coin['symbol']}[/bold]",
            f"[{score_color}]{coin['score']}[/{score_color}]",
            f"[{rsi_color}]{coin.get('rsi', 0):.0f}[/{rsi_color}]",
            f"{coin.get('atr_pct', 0):.3f}%",
            f"{coin.get('vol_ratio', 0):.1f}x",
            f"[#7C3AED]{pattern_str}[/#7C3AED]",
            coin["reasons"][0] if coin["reasons"] else "-"
        )

    console.print(table)

def display_signal(result: SignalResult):
    if result.signal == "NONE":
        return

    is_long = result.signal == "LONG"
    color = "#10B981" if is_long else "#EF4444"
    emoji = "▲" if is_long else "▼"
    conf_color = get_confidence_color(result.confidence)

    header = f"""
[bold {color}]┌─────────────────────────────────────────────────────────────┐
│  {emoji} {result.signal} SİNYAL • {result.symbol}                              │
│  Güvenilirlik: [{conf_color}]{result.confidence:.0f}% {result.confidence_level}[/{conf_color}]                          │
│  [{time.strftime('%Y-%m-%d %H:%M:%S UTC')}]                               │
└─────────────────────────────────────────────────────────────┘[/bold {color}]"""

    # Conditions with weights
    cond_lines = []
    weight_map = {
        "ema_crossover": ("EMA Cross", 30),
        "rsi_ok": ("RSI Onay", 20),
        "atr_ok": ("ATR Volatilite", 15),
        "volume_spike": ("Volume Spike", 25),
        "trigger_ok": ("Trigger Momentum", 10),
    }
    for cond, met in result.conditions.items():
        icon = "[#10B981]✓[/#10B981]" if met else "[#EF4444]✗[/#EF4444]"
        cond_name, weight = weight_map.get(cond, (cond, 0))
        score = result.condition_scores.get(cond, 0)
        cond_lines.append(f"  {icon} {cond_name} [dim]({weight} puan)[/dim] → [{conf_color}]{score}[/{conf_color}]")

    # Indicators
    ind_lines = []
    ind_names = {
        "ema_fast": "EMA Hızlı",
        "ema_slow": "EMA Yavaş",
        "rsi": "RSI",
        "atr": "ATR",
        "atr_pct": "ATR%",
        "vol_ratio": "Volume Oranı",
    }
    for name, val in result.indicators.items():
        display_name = ind_names.get(name, name)
        ind_lines.append(f"  [dim]{display_name}[/dim]: {val:.4f}")

    # Build content as text only
    content = f"""
[bold #F8FAFC]Giriş Fiyatı:[/bold #F8FAFC]  [bold {color}]{format_price(result.entry_price)}[/bold {color}]
[bold #F8FAFC]Stop Loss:[/bold #F8FAFC]     [#EF4444]{format_price(result.sl_price)}[/#EF4444]
[bold #F8FAFC]Take Profit:[/bold #F8FAFC]   [#10B981]{format_price(result.tp_price)}[/#10B981]
[bold #F8FAFC]Kaldıraç:[/bold #F8FAFC]      [#F59E0B]{result.leverage}x[/#F59E0B]
[bold #F8FAFC]Risk/Kazanç:[/bold #F8FAFC]   [bold #7C3AED]1:{result.risk_reward:.2f}[/bold #7C3AED]

[bold #7C3AED]━━━ Koşullar & Ağırlıklar ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #7C3AED]
{chr(10).join(cond_lines)}

[bold #7C3AED]━━━ İndikatörler ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #7C3AED]
{chr(10).join(ind_lines)}

[bold #F59E0B]📌 Komut:[/bold #F59E0B] python -m plugins.scalpbot track --symbol {result.symbol} --direction {result.signal} --entry {format_price(result.entry_price)} --sl {format_price(result.sl_price)} --tp {format_price(result.tp_price)}"""

    panel = Panel(
        content,
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
    color = get_pnl_color(pnl_pct)
    pnl_sign = "+" if pnl_pct >= 0 else ""
    is_profit = pnl_pct >= 0

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
    console.print()
    console.print(Panel(
        f"[#6B7280]⚡ Tarama: {scan_time:.1f}s • "
        f"📊 Sinyaller: {signal_count} • "
        f"🕐 {time.strftime('%H:%M:%S')} UTC[/#6B7280]",
        border_style="#334155",
        box=box.ROUNDED,
        padding=(0, 1)
    ))
