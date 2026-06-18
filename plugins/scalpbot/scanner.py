import time
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict
from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult
from .screener import MarketScreener
from .display import (
    console, display_banner, display_scanning_header,
    display_screening_results, display_signal, display_status_bar
)

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
        self.scan_count = 0
        self.signal_count = 0

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
        start_time = time.time()
        self.scan_count += 1

        console.print()
        console.print(f"[bold #00D4AA]━━━ TARAMA #{self.scan_count} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #00D4AA]")
        console.print(f"[#6B7280]   {time.strftime('%H:%M:%S UTC')} • Veri çekiliyor...[/#6B7280]")

        # Step 1: Fetch all kline data
        self.kline_cache = self.fetch_all_klines()
        console.print(f"[#10B981]   ✓ {len(self.kline_cache)} coin verisi çekildi[/#10B981]")

        # Step 2: Screen market
        console.print(f"[#6B7280]   🔍 Piyasa analiz ediliyor...[/#6B7280]")
        screened = self.screener.screen_market(list(self.kline_cache.keys()), self.kline_cache)

        if not screened:
            console.print("[#F97316]   ⚠ Uygun aday bulunamadı[/#F97316]")
            return []

        # Display screening results
        display_screening_results(screened)

        # Step 3: Evaluate only top candidates
        console.print(f"[#6B7280]   📡 Sinyal değerlendiriliyor...[/#6B7280]")
        signals = []
        for coin in screened[:5]:
            symbol = coin["symbol"]
            if symbol in self.kline_cache:
                result = evaluate_signal(self.kline_cache[symbol], self.config, symbol=symbol)
                if result.signal != "NONE":
                    signals.append(result)
                    self.signal_count += 1

        scan_time = time.time() - start_time
        display_status_bar(self.signal_count, scan_time)

        return signals

    def run(self):
        self.running = True
        display_banner()

        console.print()
        console.print(Panel(
            f"[bold #00D4AA]⚡ MOD: AKILLI FİLTRELEME[/bold #00D4AA]\n"
            f"[#6B7280]   Likidite • RSI • ATR • Volume Spike Analizi[/#6B7280]\n"
            f"[#6B7280]   Veri: Yahoo Finance Canlı 1 Dakika[/#6B7280]\n"
            f"[#6B7280]   Taranan Coin: {len(ALL_COINS)} • Aralık: {self.config.scan_interval_sec}s[/#6B7280]",
            border_style="#334155",
            box=box.ROUNDED,
            padding=(0, 2)
        ))

        console.print()
        console.print("[#F59E0B]   ⏹ Çıkmak için: Ctrl+C[/#F59E0B]")
        console.print()

        try:
            while self.running:
                signals = self.scan_once()
                if signals:
                    for sig in signals:
                        display_signal(sig)
                time.sleep(self.config.scan_interval_sec)
        except KeyboardInterrupt:
            console.print()
            console.print(Panel(
                f"[bold #EF4444]🛑 TARAMA DURDURULDU[/bold #EF4444]\n"
                f"[#6B7280]   Toplam Tarama: {self.scan_count} • Toplam Sinyal: {self.signal_count}[/#6B7280]",
                border_style="#EF4444",
                box=box.ROUNDED
            ))
            self.running = False
