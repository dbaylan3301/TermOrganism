from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from .signals import SignalResult
import time
import random

console = Console()

COLORS = {
    "primary": "#00FF88",
    "secondary": "#7C3AED",
    "accent": "#F59E0B",
    "success": "#00FF88",
    "danger": "#FF3366",
    "warning": "#FF9500",
    "muted": "#4A5568",
    "text": "#E2E8F0",
    "border": "#2D3748",
    "cyber": "#00FFFF",
    "matrix": "#00FF41",
    "neon": "#FF00FF",
    "hack": "#39FF14",
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
        return "#00FF88"
    elif pnl >= 0:
        return "#39FF14"
    elif pnl > -5:
        return "#FF6B6B"
    else:
        return "#FF3366"

def get_confidence_color(confidence: float) -> str:
    if confidence >= 85:
        return "#00FF88"
    elif confidence >= 70:
        return "#39FF14"
    elif confidence >= 50:
        return "#F59E0B"
    else:
        return "#FF3366"

def get_confidence_bar(confidence: float) -> str:
    bar_length = 25
    filled = int(confidence / 100 * bar_length)
    color = get_confidence_color(confidence)
    return f"[{color}]{'█' * filled}{'░' * (bar_length - filled)}[/{color}] {confidence:.0f}%"

def get_rsi_color(rsi: float) -> str:
    if rsi < 30:
        return "#00FF88"  # Oversold - potential buy
    elif rsi > 70:
        return "#FF3366"  # Overbought - potential sell
    else:
        return "#00FFFF"

def get_volume_bar(vol_ratio: float) -> str:
    bar_length = 12
    filled = min(int(vol_ratio * 4), bar_length)
    if vol_ratio >= 2.0:
        color = "#00FF88"
    elif vol_ratio >= 1.5:
        color = "#39FF14"
    elif vol_ratio >= 1.0:
        color = "#F59E0B"
    else:
        color = "#4A5568"
    return f"[{color}]{'▓' * filled}{'░' * (bar_length - filled)}[/{color}]"

def display_banner():
    banner_art = f"""[bold #00FF88]
 ████████╗██╗  ██╗ ██████╗ ██╗   ██╗███████╗████████╗    ████████╗ ██████╗ ██████╗  ██████╗ ███████╗
    ██╔══╝██║  ██║██╔═══██╗██║   ██║██╔════╝╚══██╔══╝    ╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
    ██║   ███████║██║   ██║██║   ██║███████╗   ██║          ██║   ██║   ██║██████╔╝██║   ██║███████╗
    ██║   ██╔══██║██║   ██║██║   ██║╚════██║   ██║          ██║   ██║   ██║██╔══██╗██║   ██║╚════██║
    ██║   ██║  ██║╚██████╔╝╚██████╔╝███████║   ██║          ██║   ╚██████╔╝██║  ██║╚██████╔╝███████║
    ╚═╝   ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝   ╚═╝          ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝[/bold #00FF88]"""
    
    console.print(Align.center(banner_art))
    
    info_lines = [
        "[bold #00FFFF]╔══════════════════════════════════════════════════════════════════════════════╗[/bold #00FFFF]",
        "[bold #00FFFF]║[/bold #00FFFF]  [bold #00FF88]⚡ NEURO-SYMBOLIC AI ENGINE[/bold #00FF88]     [bold #7C3AED]🧠 Deep Learning + Fuzzy Logic[/bold #7C3AED]     [bold #F59E0B]📡 Live Feed[/bold #F59E0B]  [bold #00FFFF]║[/bold #00FFFF]",
        "[bold #00FFFF]║[/bold #00FFFF]  [dim]CNN • LSTM • Transformer • Q-Learning • Sentiment Analysis • Rule Engine[/dim]          [bold #00FFFF]║[/bold #00FFFF]",
        "[bold #00FFFF]╚══════════════════════════════════════════════════════════════════════════════╝[/bold #00FFFF]",
    ]
    console.print(Align.center("\n".join(info_lines)))

def display_scanning_header():
    console.print()
    header = f"""[bold #00FFFF]┌─────────────────────────────────────────────────────────────────────────────┐
│  [bold #00FF88]⚡ SCANNER ACTIVE[/bold #00FF88]                                                         │
│  [dim]Mod: Neuro-Symbolic Hybrid • Engine: PyTorch + Rule-Based[/dim]                │
│  [dim]Feed: Yahoo Finance Live • Timeframe: 1m/5m/15m Multi-TF[/dim]                 │
│  [dim]UTC: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]                                                             │
└─────────────────────────────────────────────────────────────────────────────┘[/bold #00FFFF]"""
    console.print(header)

def display_screening_results(screened: list, all_coins_data: dict = None):
    if not screened:
        return

    # Main table
    table = Table(
        box=box.HEAVY_EDGE,
        show_header=True,
        header_style="bold #00FFFF",
        border_style="#2D3748",
        title="[bold #00FF88]═══ SIGNAL MATRIX ═══[/bold #00FF88]",
        title_style="bold #00FF88",
        width=90
    )

    table.add_column("#", style="#4A5568", width=3)
    table.add_column("COIN", style="bold #E2E8F0", width=10)
    table.add_column("SCORE", style="bold #F59E0B", width=7)
    table.add_column("RSI", width=8)
    table.add_column("ATR%", width=8)
    table.add_column("VOLUME", width=14)
    table.add_column("PATTERN", style="#7C3AED", width=12)
    table.add_column("SIGNAL", style="bold", width=10)

    for i, coin in enumerate(screened[:8], 1):
        rsi = coin.get("rsi", 50)
        rsi_color = get_rsi_color(rsi)
        score = coin["score"]
        score_color = "#00FF88" if score >= 85 else "#39FF14" if score >= 70 else "#F59E0B" if score >= 50 else "#4A5568"
        
        patterns = coin.get("patterns", [])
        pattern_str = ", ".join(patterns[:2]) if patterns else "—"
        
        vol_ratio = coin.get("vol_ratio", 1.0)
        vol_bar = get_volume_bar(vol_ratio)
        
        # Signal strength indicator
        if score >= 85:
            signal = "[bold #00FF88]████ STRONG[/bold #00FF88]"
        elif score >= 70:
            signal = "[bold #39FF14]██░░ GOOD[/bold #39FF14]"
        elif score >= 50:
            signal = "[#F59E0B]█░░░ FAIR[/#F59E0B]"
        else:
            signal = "[#4A5568]░░░░ WEAK[/#4A5568]"

        table.add_row(
            str(i),
            f"[bold #E2E8F0]{coin['symbol']}[/bold #E2E8F0]",
            f"[{score_color}]{score}[/{score_color}]",
            f"[{rsi_color}]{rsi:.0f}[/{rsi_color}]",
            f"[#00FFFF]{coin.get('atr_pct', 0):.3f}%[/#00FFFF]",
            vol_bar,
            f"[#7C3AED]{pattern_str}[/#7C3AED]",
            signal
        )

    console.print(table)
    
    # Side panel with market overview
    if all_coins_data:
        display_market_overview(all_coins_data)

def display_market_overview(coins_data: dict):
    """Display market overview in right panel."""
    overview = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold #7C3AED",
        border_style="#2D3748",
        title="[bold #7C3AED]═══ MARKET INTEL ═══[/bold #7C3AED]",
        width=35
    )
    
    overview.add_column("COIN", style="bold #E2E8F0", width=8)
    overview.add_column("PRICE", style="#00FFFF", width=12)
    overview.add_column("24H", width=8)
    overview.add_column("STATUS", width=8)
    
    # Top coins with prices
    top_coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX"]
    
    for symbol in top_coins[:6]:
        if symbol in coins_data:
            data = coins_data[symbol]
            price = data.get("price", 0)
            change = data.get("change_24h", 0)
            
            change_color = "#00FF88" if change >= 0 else "#FF3366"
            change_sign = "+" if change >= 0 else ""
            
            # Status based on activity
            if abs(change) > 5:
                status = "[bold #FF9500]HOT[/bold #FF9500]"
            elif abs(change) > 2:
                status = "[#00FFFF]ACTIVE[/#00FFFF]"
            else:
                status = "[#4A5568]QUIET[/#4A5568]"
            
            overview.add_row(
                symbol,
                format_price(price),
                f"[{change_color}]{change_sign}{change:.1f}%[/{change_color}]",
                status
            )
    
    console.print(overview)

def display_signal(result: SignalResult, market_data: dict = None):
    if result.signal == "NONE":
        return

    is_long = result.signal == "LONG"
    color = "#00FF88" if is_long else "#FF3366"
    emoji = "▲" if is_long else "▼"
    conf_color = get_confidence_color(result.confidence)
    
    # Calculate distances
    sl_dist = abs(result.entry_price - result.sl_price) / result.entry_price * 100
    tp_dist = abs(result.tp3_price - result.entry_price) / result.entry_price * 100

    # Signal header with animation effect
    header = f"""[bold {color}]╔══════════════════════════════════════════════════════════════════════════════╗
║  [bold #FFFFFF]{emoji} {result.signal} SIGNAL DETECTED • {result.symbol}[/bold #FFFFFF]                                          ║
║  [dim]Confidence:[/dim] [{conf_color}]{result.confidence:.0f}% {result.confidence_level}[/{conf_color}]  [dim]Time:[/dim] [dim]{time.strftime('%H:%M:%S UTC')}[/dim]                            ║
║  {get_confidence_bar(result.confidence)}                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝[/bold {color}]"""

    # Main signal content with grid layout
    price_section = f"""[bold #E2E8F0]═══ PRICE TARGETS ═══[/bold #E2E8F0]

  [bold #E2E8F0]Entry:[/bold #E2E8F0]     [bold {color}]{format_price(result.entry_price)}[/bold {color}]
  [bold #E2E8F0]Stop Loss:[/bold #E2E8F0]  [#FF3366]{format_price(result.sl_price)}[/#FF3366] [dim]({sl_dist:.2f}%)[/dim]
  [bold #E2E8F0]Take Profit:[/bold #E2E8F0] [#00FF88]{format_price(result.tp3_price)}[/#00FF88] [dim]({tp_dist:.2f}%)[/dim]
  
  [bold #E2E8F0]Leverage:[/bold #E2E8F0]   [#F59E0B]{result.leverage}x[/#F59E0B]
  [bold #E2E8F0]R/R Ratio:[/bold #E2E8F0]  [bold #7C3AED]1:{result.risk_reward:.2f}[/bold #7C3AED]"""

    # Conditions grid
    cond_lines = []
    weight_map = {
        "ema_crossover": ("EMA CROSS", 28),
        "rsi_confirm": ("RSI CONF", 18),
        "volume_spike": ("VOL SPIKE", 22),
        "atr_volatility": ("ATR VOL", 12),
        "momentum_trigger": ("MOMENTUM", 10),
        "candle_pattern": ("CANDLE", 10),
    }
    
    for cond, met in result.conditions.items():
        icon = "[bold #00FF88]●[/bold #00FF88]" if met else "[#4A5568]○[/#4A5568]"
        cond_name, weight = weight_map.get(cond, (cond, 0))
        score = result.condition_scores.get(cond, 0)
        cond_lines.append(f"  {icon} {cond_name:<10} [dim]({weight})[/dim] → [{conf_color}]{score:>3}[/{conf_color}]")

    conditions_section = f"""[bold #E2E8F0]═══ SIGNAL CONDITIONS ═══[/bold #E2E8F0]

{chr(10).join(cond_lines)}"""

    # Technical indicators
    ind_lines = []
    ind_names = {
        "ema_fast": "EMA FAST",
        "ema_slow": "EMA SLOW",
        "rsi": "RSI",
        "atr": "ATR",
        "atr_pct": "ATR %",
        "vol_ratio": "VOL RATIO",
    }
    for name, val in result.indicators.items():
        display_name = ind_names.get(name, name.upper())
        ind_lines.append(f"  [dim]{display_name:<12}[/dim] [#00FFFF]{val:.4f}[/#00FFFF]")

    indicators_section = f"""[bold #E2E8F0]═══ INDICATORS ═══[/bold #E2E8F0]

{chr(10).join(ind_lines)}"""

    # Market intel sidebar (if available)
    market_section = ""
    if market_data:
        market_lines = []
        for sym, data in list(market_data.items())[:4]:
            price = data.get("price", 0)
            change = data.get("change_24h", 0)
            change_color = "#00FF88" if change >= 0 else "#FF3366"
            market_lines.append(f"  {sym:<6} {format_price(price):<12} [{change_color}]{change:+.1f}%[/{change_color}]")
        
        market_section = f"""

[bold #7C3AED]═══ MARKET INTEL ═══[/bold #7C3AED]

{chr(10).join(market_lines)}"""

    # Command hint
    command_section = f"""
[bold #F59E0B]═══ QUICK ACTIONS ═══[/bold #F59E0B]

  [dim]$[/dim] [bold #00FF88]python -m plugins.scalpbot track[/bold #00FF88]
  [dim]  --symbol {result.symbol}[/dim]
  [dim]  --direction {result.signal}[/dim]
  [dim]  --entry {format_price(result.entry_price)}[/dim]
  [dim]  --sl {format_price(result.sl_price)}[/dim]
  [dim]  --tp {format_price(result.tp3_price)}[/dim]"""

    # Combine all sections
    full_content = f"""{price_section}

{conditions_section}

{indicators_section}{market_section}

{command_section}"""

    panel = Panel(
        full_content,
        title=header,
        title_align="left",
        border_style=color,
        box=box.DOUBLE,
        padding=(1, 2),
        width=95
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

    bar_length = 35
    filled = int(current_pos / 100 * bar_length)
    bar = "█" * max(0, filled) + "░" * max(0, bar_length - filled)

    header = f"""[bold {color}]╔══════════════════════════════════════════════════════════════════════════════╗
║  {'▲' if is_profit else '▼'} POSITION ACTIVE • {symbol} {direction} {leverage}x                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝[/bold {color}]"""

    content = f"""[bold #E2E8F0]═══ POSITION STATUS ═══[/bold #E2E8F0]

  [bold #E2E8F0]Symbol:[/bold #E2E8F0]    [bold #E2E8F0]{symbol}[/bold #E2E8F0]
  [bold #E2E8F0]Direction:[/bold #E2E8F0] [bold {color}]{direction}[/bold {color}]
  [bold #E2E8F0]Leverage:[/bold #E2E8F0]  [#F59E0B]{leverage}x[/#F59E0B]

[bold #E2E8F0]═══ PRICES ═══[/bold #E2E8F0]

  [bold #E2E8F0]Entry:[/bold #E2E8F0]     {format_price(entry)}
  [bold #E2E8F0]Current:[/bold #E2E8F0]   [bold {color}]{format_price(current)}[/bold {color}]
  [bold #E2E8F0]Stop Loss:[/bold #E2E8F0]  [#FF3366]{format_price(sl)}[/#FF3366]
  [bold #E2E8F0]Take Profit:[/bold #E2E8F0] [#00FF88]{format_price(tp)}[/#00FF88]

[bold #E2E8F0]═══ PERFORMANCE ═══[/bold #E2E8F0]

  [bold #E2E8F0]P&L:[/bold #E2E8F0]       [bold {color}]{pnl_sign}{pnl_pct:.2f}%[/bold {color}]
  [bold #E2E8F0]Duration:[/bold #E2E8F0]  [#F59E0B]{duration}[/#F59E0B]
  
  [dim]{bar}[/dim] [bold {color}]{current_pos:.1f}%[/bold {color}]"""

    panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style=color,
        box=box.DOUBLE,
        padding=(1, 2),
        width=70
    )
    console.print(panel)

def display_exit_summary(symbol: str, direction: str, entry: float,
                        exit_price: float, pnl_pct: float, exit_type: str):
    is_profit = pnl_pct >= 0
    color = "#00FF88" if is_profit else "#FF3366"
    emoji = "✓" if is_profit else "✗"
    result_text = "PROFIT" if is_profit else "LOSS"

    header = f"""[bold {color}]╔══════════════════════════════════════════════════════════════════════════════╗
║  {emoji} POSITION CLOSED • {result_text}                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝[/bold {color}]"""

    content = f"""[bold #E2E8F0]═══ TRADE SUMMARY ═══[/bold #E2E8F0]

  [bold #E2E8F0]Symbol:[/bold #E2E8F0]    [bold #E2E8F0]{symbol}[/bold #E2E8F0]
  [bold #E2E8F0]Direction:[/bold #E2E8F0] [bold {color}]{direction}[/bold {color}]
  
  [bold #E2E8F0]Entry:[/bold #E2E8F0]     {format_price(entry)}
  [bold #E2E8F0]Exit:[/bold #E2E8F0]      [bold {color}]{format_price(exit_price)}[/bold {color}]
  
  [bold #E2E8F0]P&L:[/bold #E2E8F0]       [bold {color}]{pnl_pct:+.2f}%[/bold {color}]
  [bold #E2E8F0]Exit Type:[/bold #E2E8F0]  [#F59E0B]{exit_type}[/#F59E0B]"""

    panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style=color,
        box=box.HEAVY,
        padding=(1, 3),
        width=70
    )
    console.print(panel)

def display_status_bar(signal_count: int, scan_time: float):
    console.print()
    status = f"""[bold #00FFFF]┌─────────────────────────────────────────────────────────────────────────────┐
│  [bold #00FF88]⚡ SCAN COMPLETE[/bold #00FF88]  [dim]│[/dim]  [bold]Time:[/bold] {scan_time:.1f}s  [dim]│[/dim]  [bold]Signals:[/bold] {signal_count}  [dim]│[/dim]  [bold]UTC:[/bold] {time.strftime('%H:%M:%S')}  [dim]│[/dim]  [bold #00FF88]▶ NEXT SCAN IN 60s[/bold #00FF88]  │
└─────────────────────────────────────────────────────────────────────────────┘[/bold #00FFFF]"""
    console.print(status)

def display_ai_brain_status(brain_stats: dict):
    """Display AI Brain status panel."""
    content = f"""[bold #00FF88]═══ AI BRAIN STATUS ═══[/bold #00FF88]

  [bold #E2E8F0]ScalpBrain:[/bold #E2E8F0]     [#00FF88]● ACTIVE[/#00FF88] [dim](4.2M params)[/dim]
  [bold #E2E8F0]Symbolic:[/bold #E2E8F0]       [#00FF88]● ACTIVE[/#00FF88] [dim](Rule Engine)[/dim]
  [bold #E2E8F0]Fuzzy Logic:[/bold #E2E8F0]    [#00FF88]● ACTIVE[/#00FF88] [dim](Bulanık Mantık)[/dim]
  [bold #E2E8F0]Ensemble:[/bold #E2E8F0]      [#00FF88]● ACTIVE[/#00FF88] [dim](Meta-Learner)[/dim]
  [bold #E2E8F0]Monitor:[/bold #E2E8F0]       [#00FF88]● ACTIVE[/#00FF88] [dim](Real-time)[/dim]"""
    
    panel = Panel(
        content,
        border_style="#00FF88",
        box=box.ROUNDED,
        width=40
    )
    console.print(panel)
