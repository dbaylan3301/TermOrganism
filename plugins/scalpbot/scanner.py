import time
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List
from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult

TOP_COINS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "DOGE-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
    "LTC-USD", "ATOM-USD", "NEAR-USD", "FIL-USD", "ETC-USD",
    "BCH-USD", "ALGO-USD", "XLM-USD", "VET-USD", "HBAR-USD"
]

class CoinScanner:
    def __init__(self, config: ScalpConfig, mock: bool = False):
        self.config = config
        self.running = False
        self.mock = mock

    def fetch_usdt_pairs(self) -> List[str]:
        if self.mock:
            return [s.replace("-USD", "") for s in TOP_COINS[:self.config.top_pairs]]
        return [s.replace("-USD", "") for s in TOP_COINS[:self.config.top_pairs]]

    def fetch_klines(self, symbol: str) -> pd.DataFrame:
        if self.mock:
            return self._generate_mock_klines(symbol)
        try:
            ticker = yf.Ticker(f"{symbol}-USD")
            df = ticker.history(period="1d", interval="1m")
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume"
            })
            return df[["open", "high", "low", "close", "volume"]].tail(self.config.kline_limit)
        except Exception as e:
            print(f"⚠️ Kline alınamadı ({symbol}): {e}")
            return pd.DataFrame()

    def _generate_mock_klines(self, symbol: str) -> pd.DataFrame:
        np.random.seed(hash(symbol) % 2**31)
        n = self.config.kline_limit
        base_prices = {
            "BTC": 67000, "ETH": 3500, "SOL": 145, "BNB": 580, "XRP": 0.52,
            "DOGE": 0.12, "ADA": 0.45, "AVAX": 35, "DOT": 7.2, "LINK": 14.5
        }
        base = base_prices.get(symbol, 100)
        trend = np.random.choice([-0.001, 0, 0.001])
        closes = base + np.cumsum(np.random.randn(n) * base * 0.002 + base * trend)
        highs = closes * (1 + np.abs(np.random.randn(n) * 0.003))
        lows = closes * (1 - np.abs(np.random.randn(n) * 0.003))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = np.random.uniform(500000, 5000000, n)
        return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes})

    def scan_once(self) -> List[SignalResult]:
        pairs = self.fetch_usdt_pairs()
        if not pairs:
            return []
        signals = []
        for symbol in pairs:
            df = self.fetch_klines(symbol)
            if df.empty or len(df) < 50:
                continue
            result = evaluate_signal(df, self.config, symbol=symbol)
            if result.signal != "NONE":
                signals.append(result)
        return signals

    def run(self):
        self.running = True
        print("🔍 5x Scalp Bot başlatılıyor...")
        print("   Veri kaynağı: Yahoo Finance (canlı)")
        print(f"   Taranan çift sayısı: {len(TOP_COINS[:self.config.top_pairs])}")
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
