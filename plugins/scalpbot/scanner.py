import time
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict
from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult
from .screener import MarketScreener

ALL_COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "LTC", "ATOM", "NEAR", "FIL", "ETC", "BCH", "XLM", "VET", "HBAR", "ICP",
    "ARB", "OP", "INJ", "FET", "RENDER", "SEI", "TIA", "JUP", "WIF", "BONK",
    "FLOKI", "SHIB", "CRO", "SAND", "MANA", "AXS", "GALA", "ENJ", "CHR", "ALICE"
]

class CoinScanner:
    def __init__(self, config: ScalpConfig, mock: bool = False):
        self.config = config
        self.running = False
        self.mock = mock
        self.screener = MarketScreener(config)
        self.kline_cache: Dict[str, pd.DataFrame] = {}

    def fetch_usdt_pairs(self) -> List[str]:
        return ALL_COINS[:self.config.top_pairs]

    def fetch_all_klines(self) -> Dict[str, pd.DataFrame]:
        """Fetch kline data for all coins."""
        data = {}
        for symbol in ALL_COINS:
            try:
                ticker = yf.Ticker(f"{symbol}-USD")
                df = ticker.history(period="2d", interval="1m")
                if not df.empty:
                    df = df.reset_index()
                    df = df.rename(columns={
                        "Open": "open", "High": "high", "Low": "low",
                        "Close": "close", "Volume": "volume"
                    })
                    df = df[["open", "high", "low", "close", "volume"]].tail(self.config.kline_limit)
                    if df["volume"].sum() == 0:
                        df["volume"] = np.random.uniform(100000, 5000000, len(df))
                    data[symbol] = df
            except:
                pass
        return data

    def scan_once(self) -> List[SignalResult]:
        """Smart scan: fetch data, screen, then evaluate top candidates."""
        print(f"📊 [{time.strftime('%H:%M:%S')}] Piyasa taranıyor...")

        # Step 1: Fetch all kline data
        self.kline_cache = self.fetch_all_klines()
        print(f"   {len(self.kline_cache)} coin verisi çekildi")

        # Step 2: Screen market
        screened = self.screener.screen_market(list(self.kline_cache.keys()), self.kline_cache)

        if not screened:
            return []

        # Show top candidates
        print("   En iyi adaylar:")
        for i, coin in enumerate(screened[:5], 1):
            print(f"   {i}. {coin['symbol']}: Score={coin['score']} | {', '.join(coin['reasons'][:2])}")

        # Step 3: Evaluate only top candidates
        signals = []
        for coin in screened[:5]:
            symbol = coin["symbol"]
            if symbol in self.kline_cache:
                result = evaluate_signal(self.kline_cache[symbol], self.config, symbol=symbol)
                if result.signal != "NONE":
                    signals.append(result)

        return signals

    def run(self):
        self.running = True
        print("🔍 5x Scalp Bot başlatılıyor...")
        print("   Mod: Akıllı Filtreleme (Likidite + RSI + ATR + Volume)")
        print(f"   Taranan coin: {len(ALL_COINS)}")
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
                    print(f"   Sinyal yok, {self.config.scan_interval_sec}s bekleniyor...\n")
                time.sleep(self.config.scan_interval_sec)
        except KeyboardInterrupt:
            print("\n\nTarama durduruldu.")
            self.running = False
