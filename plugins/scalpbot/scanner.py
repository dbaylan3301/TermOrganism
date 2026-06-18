import time
import requests
import pandas as pd
from typing import List
from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult

class CoinScanner:
    def __init__(self, config: ScalpConfig):
        self.config = config
        self.running = False

    def fetch_usdt_pairs(self) -> List[str]:
        try:
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            tickers = resp.json()

            usdt_pairs = [
                t["symbol"] for t in tickers
                if t["symbol"].endswith("USDT")
                and float(t.get("quoteVolume", 0)) > 0
            ]

            usdt_pairs.sort(
                key=lambda s: float(
                    next(t["quoteVolume"] for t in tickers if t["symbol"] == s)
                ),
                reverse=True
            )
            return usdt_pairs[:self.config.top_pairs]
        except Exception as e:
            print(f"⚠️ Pair listesi alınamadı: {e}")
            return []

    def fetch_klines(self, symbol: str) -> pd.DataFrame:
        try:
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": symbol,
                "interval": self.config.kline_interval,
                "limit": self.config.kline_limit,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore"
            ])

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            print(f"⚠️ Kline alınamadı ({symbol}): {e}")
            return pd.DataFrame()

    def scan_once(self) -> List[SignalResult]:
        pairs = self.fetch_usdt_pairs()
        if not pairs:
            return []

        signals = []
        for symbol in pairs:
            df = self.fetch_klines(symbol)
            if df.empty:
                continue

            result = evaluate_signal(df, self.config, symbol=symbol)
            if result.signal != "NONE":
                signals.append(result)

        return signals

    def run(self):
        self.running = True
        print("🔍 5x Scalp Bot başlatılıyor...")
        print(f"   Taranan çift sayısı: {self.config.top_pairs}")
        print(f"   Tarama aralığı: {self.config.scan_interval_sec}s")
        print("   Çıkmak için: Ctrl+C\n")

        try:
            while self.running:
                signals = self.scan_once()

                if signals:
                    for sig in signals:
                        from .display import display_signal
                        display_signal(sig)
                        print()
                else:
                    print(f"⏳ [{time.strftime('%H:%M:%S')}] Sinyal yok, bekleniyor...")

                time.sleep(self.config.scan_interval_sec)

        except KeyboardInterrupt:
            print("\n\nTarama durduruldu.")
            self.running = False
