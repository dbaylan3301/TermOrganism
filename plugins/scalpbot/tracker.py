import time
import requests
from datetime import datetime, timedelta
from typing import Optional
from .config import ScalpConfig
from .risk import calculate_pnl, check_exit
from .display import display_position, display_exit_summary, format_price

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
        print(f"\n📊 Pozisyon takibi başlatıldı: {direction} {symbol}")
        print(f"   Giriş: {format_price(entry_price)}")
        print(f"   SL: {format_price(sl_price)} | TP: {format_price(tp_price)}")
        print("   Çıkmak için: Ctrl+C\n")

    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            url = f"https://fapi.binance.com/fapi/v1/ticker/price"
            params = {"symbol": symbol}
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception as e:
            print(f"⚠️ Fiyat alınamadı: {e}")
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
            print("Aktif pozisyon yok")
            return

        pos = self.active_position
        print("Canlı takip başlatıldı... (Ctrl+C ile çık)")

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
            print("\n\nTakip durduruldu.")
            if self.active_position:
                current_price = self.get_current_price(pos["symbol"])
                if current_price:
                    pnl = calculate_pnl(
                        pos["entry"], current_price,
                        pos["direction"], pos["leverage"]
                    )
                    print(f"Mevcut P&L: {pnl:+.2f}%")