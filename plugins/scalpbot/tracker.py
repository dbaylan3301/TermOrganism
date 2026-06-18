import time
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from .config import ScalpConfig
from .risk import calculate_pnl, check_exit
from .display import display_position, display_exit_summary, format_price, console
from rich.panel import Panel
from rich import box

class PositionTracker:
    def __init__(self, config: ScalpConfig):
        self.config = config
        self.active_position = None

    def start_tracking(self, symbol: str, direction: str, entry_price: float,
                       sl_price: float, tp_price: float, leverage: int):
        self.active_position = {
            "symbol": symbol,
            "direction": direction,
            "entry": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "leverage": leverage,
            "start_time": datetime.now(),
        }

        console.print()
        console.print(Panel(
            f"[bold #00D4AA]⚡ POZİYON TAKİBİ BAŞLATILDI[/bold #00D4AA]\n\n"
            f"[bold #F8FAFC]   {direction} {symbol} {leverage}x[/bold #F8FAFC]\n\n"
            f"[#6B7280]   Giriş:  [#F8FAFC]{format_price(entry_price)}[/#F8FAFC]\n"
            f"[#6B7280]   SL:     [#EF4444]{format_price(sl_price)}[/#EF4444]\n"
            f"[#6B7280]   TP:     [#10B981]{format_price(tp_price)}[/#10B981]\n\n"
            f"[#F59E0B]   ⏹ Çıkmak için: Ctrl+C[/#F59E0B]",
            border_style="#00D4AA",
            box=box.ROUNDED,
            padding=(0, 2)
        ))
        console.print()

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = yf.Ticker(f"{symbol}-USD")
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                return float(data["Close"].iloc[-1])
            return None
        except Exception as e:
            console.print(f"[#F97316]   ⚠ Fiyat alınamadı: {e}[/#F97316]")
            return None

    def format_duration(self, seconds: float) -> str:
        td = timedelta(seconds=int(seconds))
        hours, remainder = divmod(td.seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}sa {minutes}dk {secs}sn"
        return f"{minutes}dk {secs}sn"

    def run(self):
        if not self.active_position:
            console.print("[#EF4444]   Aktif pozisyon yok[/#EF4444]")
            return

        pos = self.active_position
        console.print("[#6B7280]   📡 Canlı takip başlatıldı...[/#6B7280]")
        console.print()

        try:
            while True:
                current_price = self.get_current_price(pos["symbol"])
                if current_price is None:
                    time.sleep(self.config.price_refresh_sec)
                    continue

                pnl = calculate_pnl(
                    pos["entry"], current_price,
                    pos["direction"], pos["leverage"]
                )

                elapsed = (datetime.now() - pos["start_time"]).total_seconds()
                duration = self.format_duration(elapsed)

                display_position(
                    symbol=pos["symbol"],
                    direction=pos["direction"],
                    entry=pos["entry"],
                    current=current_price,
                    sl=pos["sl"],
                    tp=pos["tp"],
                    leverage=pos["leverage"],
                    duration=duration,
                    pnl_pct=pnl,
                )

                exit_type = check_exit(
                    pos["entry"], current_price,
                    pos["sl"], pos["tp"], pos["direction"]
                )

                if exit_type:
                    display_exit_summary(
                        symbol=pos["symbol"],
                        direction=pos["direction"],
                        entry=pos["entry"],
                        exit_price=current_price,
                        pnl_pct=pnl,
                        exit_type=exit_type,
                    )
                    self.active_position = None
                    break

                time.sleep(self.config.price_refresh_sec)

        except KeyboardInterrupt:
            console.print()
            console.print(Panel(
                f"[bold #EF4444]🛑 TAKİP DURDURULDU[/bold #EF4444]",
                border_style="#EF4444",
                box=box.ROUNDED
            ))
            if self.active_position:
                current_price = self.get_current_price(pos["symbol"])
                if current_price:
                    pnl = calculate_pnl(
                        pos["entry"], current_price,
                        pos["direction"], pos["leverage"]
                    )
                    console.print(f"[#6B7280]   Mevcut P&L: {pnl:+.2f}%[/#6B7280]")
