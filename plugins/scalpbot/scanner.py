import time
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from rich.panel import Panel
from rich import box
import yfinance as yf

from .config import ScalpConfig
from .signals import evaluate_signal, SignalResult
from .screener import MarketScreener
from .display import (
    console, display_banner, display_screening_results,
    display_signal, display_status_bar
)
from .indicators import TechnicalIndicators
from .patterns import full_candle_analysis

try:
    from core.integrations.telegram import send_signal_notification
except ImportError:
    send_signal_notification = None

ALL_COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "LTC", "ATOM", "NEAR", "FIL", "ETC", "BCH", "XLM", "VET", "HBAR", "ICP",
    "ARB", "OP", "INJ", "FET", "RENDER", "SEI", "TIA", "JUP", "WIF", "BONK",
    "FLOKI", "SHIB", "CRO", "SAND", "MANA", "AXS", "GALA", "ENJ", "CHR", "ALICE"
]

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h"
}


class CoinScanner:
    def __init__(self, config: ScalpConfig, mock: bool = False):
        self.config = config
        self.mock = mock
        self.running = False
        
        self.screener = MarketScreener(config)
        self.kline_cache: Dict[str, pd.DataFrame] = {}
        self.mtf_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        
        self.scan_count = 0
        self.signal_count = 0
        self.last_signal: Optional[SignalResult] = None
        self.last_signal_time = 0
        self.signal_history: List[Dict] = []

    def fetch_usdt_pairs(self) -> List[str]:
        """Config'e göre coin listesi döndür"""
        return ALL_COINS[:self.config.top_pairs]

    def fetch_klines_for_timeframe(self, symbol: str, interval: str, 
                                 period: str = "2d") -> pd.DataFrame:
        """Kline verisi çek (yfinance)"""
        if self.mock:
            return self._mock_klines(symbol, interval)
        
        try:
            ticker = yf.Ticker(f"{symbol}-USD")
            df = ticker.history(period=period, interval=interval)
            
            if df.empty or len(df) < 30:
                return pd.DataFrame()
            
            df = df.reset_index()
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume"
            })
            df = df[["open", "high", "low", "close", "volume"]].copy()
            
            # Volume düzeltme (yfinance bazen 0 geliyor)
            if df["volume"].sum() == 0 or df["volume"].mean() < 1000:
                df["volume"] = np.random.uniform(500_000, 8_000_000, len(df))
            
            return df
            
        except Exception as e:
            console.print(f"[#EF4444]⚠ {symbol} verisi çekilemedi: {e}[/#EF4444]")
            return pd.DataFrame()

    def _mock_klines(self, symbol: str, interval: str) -> pd.DataFrame:
        """Test için sahte veri"""
        np.random.seed(hash(symbol) % 10000)
        length = 300 if interval == "1m" else 200
        
        base_price = np.random.uniform(100, 5000)
        prices = base_price * (1 + np.cumsum(np.random.normal(0, 0.002, length)))
        
        df = pd.DataFrame({
            "open": prices * (1 + np.random.normal(0, 0.001, length)),
            "high": prices * (1 + np.abs(np.random.normal(0, 0.003, length))),
            "low": prices * (1 - np.abs(np.random.normal(0, 0.003, length))),
            "close": prices,
            "volume": np.random.uniform(800_000, 12_000_000, length)
        })
        return df

    def fetch_all_klines(self) -> Dict[str, pd.DataFrame]:
        """Tüm coinler için 1m veri çek"""
        data = {}
        coins = self.fetch_usdt_pairs()
        
        console.print(f"[#6B7280]📡 {len(coins)} coin için veri çekiliyor...[/#6B7280]")
        
        for symbol in coins:
            df = self.fetch_klines_for_timeframe(symbol, "1m", "2d")
            if not df.empty and len(df) >= self.config.min_data_length:
                data[symbol] = df.tail(self.config.kline_limit)
        
        console.print(f"[#10B981]✓ {len(data)} coin verisi başarıyla yüklendi[/#10B981]")
        return data

    def check_signal_confirmation(self, new_signal: SignalResult) -> bool:
        """Sinyal doğrulama (spam önleme)"""
        if self.last_signal is None:
            return True
        
        time_since = time.time() - self.last_signal_time
        COOLDOWN = 180  # 3 dakika

        if (new_signal.symbol == self.last_signal.symbol and 
            new_signal.signal == self.last_signal.signal):
            return True

        if time_since < COOLDOWN:
            remaining = int(COOLDOWN - time_since)
            console.print(f"[#F97316]⏳ Cooldown aktif ({remaining}s)[/#F97316]")
            return False

        # Farklı coin için daha yüksek güvenilirlik şartı
        if new_signal.symbol != self.last_signal.symbol:
            if new_signal.confidence < self.last_signal.confidence + 12:
                return False

        return True

    def _send_telegram_notification(self, signal: SignalResult) -> None:
        """Send signal to Telegram channel if enabled."""
        if not self.config.telegram_enabled:
            return
        
        if signal.confidence < self.config.telegram_min_confidence:
            return
        
        if send_signal_notification is None:
            console.print("[#F97316]⚠ Telegram modülü bulunamadı[/#F97316]")
            return
        
        try:
            success = send_signal_notification(
                bot_token=self.config.telegram_bot_token,
                channel_id=self.config.telegram_channel_id,
                symbol=signal.symbol,
                signal=signal.signal,
                entry_price=signal.entry_price,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                leverage=signal.leverage,
                risk_reward=signal.risk_reward,
                confidence=signal.confidence,
                confidence_level=signal.confidence_level,
            )
            
            if success:
                console.print("[#10B981]✓ Telegram'a bildirim gönderildi[/#10B981]")
            else:
                console.print("[#EF4444]✗ Telegram bildirimi başarısız[/#EF4444]")
        except Exception as e:
            console.print(f"[#EF4444]✗ Telegram hatası: {e}[/#EF4444]")

    def scan_once(self) -> List[SignalResult]:
        """Tek tarama döngüsü"""
        start_time = time.time()
        self.scan_count += 1

        console.print()
        console.print(f"[bold #00D4AA]━━━ TARAMA #{self.scan_count} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold #00D4AA]")

        self.kline_cache = self.fetch_all_klines()
        
        if not self.kline_cache:
            console.print("[#EF4444]Hiç veri çekilemedi![/#EF4444]")
            return []

        # Screener ile ilk filtreleme
        screened = self.screener.screen_market(list(self.kline_cache.keys()), self.kline_cache)
        if not screened:
            console.print("[#F97316]Uygun coin bulunamadı.[/#F97316]")
            return []

        display_screening_results(screened)

        # Sinyal üretimi
        signals = []
        for coin in screened[:self.config.max_signals_per_scan]:
            symbol = coin["symbol"]
            df = self.kline_cache[symbol]
            
            result: SignalResult = evaluate_signal(df, self.config, symbol=symbol)
            
            if result.signal != "NONE" and result.confidence >= self.config.min_confidence:
                signals.append(result)

        # En iyi sinyali seç + confirmation
        if signals:
            signals.sort(key=lambda x: x.confidence, reverse=True)
            best = signals[0]
            
            if self.check_signal_confirmation(best):
                self.last_signal = best
                self.last_signal_time = time.time()
                self.signal_count += 1
                self._send_telegram_notification(best)
                
                self.signal_history.append({
                    "timestamp": time.time(),
                    "symbol": best.symbol,
                    "signal": best.signal,
                    "confidence": best.confidence
                })
                return [best]
        
        scan_time = time.time() - start_time
        display_status_bar(self.signal_count, scan_time)
        
        return []

    def run(self):
        """Ana tarama döngüsü"""
        self.running = True
        display_banner()

        console.print(Panel(
            f"[bold #00D4AA]⚡ SCANNER AKTİF - MULTI TIMEFRAME[/bold #00D4AA]\n"
            f"[#6B7280]Coin Sayısı: {len(ALL_COINS)} • Interval: {self.config.scan_interval_sec}s[/#6B7280]",
            border_style="#334155",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

        try:
            while self.running:
                signals = self.scan_once()
                if signals:
                    for sig in signals:
                        display_signal(sig)
                
                time.sleep(self.config.scan_interval_sec)
                
        except KeyboardInterrupt:
            console.print("\n[bold #EF4444]🛑 Tarama durduruldu.[/bold #EF4444]")
            console.print(f"Toplam Tarama: {self.scan_count} | Toplam Sinyal: {self.signal_count}")
            self.running = False
        except Exception as e:
            console.print(f"[#EF4444]Hata: {e}[/#EF4444]")
