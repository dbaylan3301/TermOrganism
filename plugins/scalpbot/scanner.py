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
from .adaptive import AdaptiveManager
from .logger import TradeLogger, SignalQualityLogger
from .regime import RegimeDetector
from .ml_engine import MLEnsemble
from .exchange import ExchangeClient
from .paper_trading import PaperTrader, get_paper_trader
from .brain import TradingBrain

try:
    from core.integrations.telegram import send_signal_notification, send_leaderboard_notification
except ImportError:
    send_signal_notification = None
    send_leaderboard_notification = None

try:
    from plugins.scalpbot.ai.brain import MetaBrain
    AI_BRAIN_AVAILABLE = True
except ImportError:
    AI_BRAIN_AVAILABLE = False

# NinjaTrade - Haber takibi için coin isimleri
NINJA_COINS = {
    "BTC": ["Bitcoin", "BTC"], "ETH": ["Ethereum", "ETH"], "SOL": ["Solana", "SOL"],
    "BNB": ["Binance", "BNB"], "XRP": ["Ripple", "XRP"], "ADA": ["Cardano", "ADA"],
    "DOGE": ["Dogecoin", "DOGE"], "AVAX": ["Avalanche", "AVAX"], "DOT": ["Polkadot", "DOT"],
    "LINK": ["Chainlink", "LINK"], "ATOM": ["Cosmos", "ATOM"], "NEAR": ["NEAR", "NEAR"],
    "FIL": ["Filecoin", "FIL"], "ARB": ["Arbitrum", "ARB"], "OP": ["Optimism", "OP"],
    "INJ": ["Injective", "INJ"], "FET": ["Fetch.ai", "FET"], "RENDER": ["Render", "RENDER"],
    "SEI": ["Sei", "SEI"], "TIA": ["Celestia", "TIA"], "JUP": ["Jupiter", "JUP"],
    "WIF": ["dogwifhat", "WIF"], "BONK": ["Bonk", "BONK"], "SHIB": ["Shiba", "SHIB"],
    "SAND": ["Sandbox", "SAND"], "MANA": ["Decentraland", "MANA"], "AXS": ["Axie", "AXS"],
    "GALA": ["Gala", "GALA"], "ENJ": ["Enjin", "ENJ"], "CHR": ["Chromia", "CHR"],
}

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
        
        # Adaptive manager
        self.adaptive = AdaptiveManager(config) if config.adaptive_enabled else None
        
        # Periyodik ayarlama için sayaç
        self.adapt_interval = 10
        self.scan_since_adapt = 0
        
        # Telegram post limiti
        self.posts_today = 0
        self.last_post_time = 0
        self.post_reset_time = time.time()
        
        # Logger
        self.trade_logger = TradeLogger(config.log_dir) if config.logging_enabled else None
        self.quality_logger = SignalQualityLogger(self.trade_logger) if self.trade_logger else None
        
        # Regime detector
        self.regime_detector = RegimeDetector(
            adx_period=config.regime_adx_period,
            atr_period=config.atr_period
        )
        
        # ML Engine
        self.ml_engine = MLEnsemble()
        self.ml_trained = False
        
        # Exchange client
        self.exchange = ExchangeClient("mexc")
        
        # NinjaTrade takip listesi
        self._tracked_coins: Dict[str, Dict] = {}
        
        # Paper Trader
        self.paper_trader = get_paper_trader()
        self.trading_active = True
        
        # Trading Brain
        self.brain = TradingBrain(config)

    def train_ml_models(self) -> Dict:
        """ML modellerini eğit."""
        console.print("[#3B82F6]🧠 ML modelleri eğitiliyor...[/#3B82F6]")
        
        # Tüm coinlerin verisini birleştir
        all_data = []
        for symbol in self.fetch_usdt_pairs()[:20]:
            df = self.fetch_klines_for_timeframe(symbol, "15m", "30d")
            if not df.empty and len(df) > 200:
                df['symbol'] = symbol
                all_data.append(df)
        
        if not all_data:
            return {"status": "error", "message": "Yetersiz veri"}
        
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # ML eğitimi
        result = self.ml_engine.train(combined_df)
        
        if result["status"] == "success":
            self.ml_trained = True
            console.print(f"[#10B981]✓ ML eğitimi tamamlandı - Accuracy: %{result['ensemble_accuracy']}[/#10B981]")
            
            # Modeli kaydet
            self.ml_engine.save("ml_model.pkl")
        else:
            console.print(f"[#EF4444]✗ ML eğitimi başarısız: {result.get('message')}[/#EF4444]")
        
        return result

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
        """Test için gerçekçi fiyatlarla sahte veri"""
        MOCK_PRICES = {
            "BTC": 65000, "ETH": 3500, "SOL": 180, "BNB": 600, "XRP": 0.62,
            "DOGE": 0.33, "ADA": 0.45, "AVAX": 35, "DOT": 7, "LINK": 14,
            "LTC": 85, "ATOM": 9, "NEAR": 7, "FIL": 6, "ETC": 28,
            "BCH": 450, "XLM": 0.11, "VET": 0.035, "HBAR": 0.08, "ICP": 12,
            "ARB": 1.1, "OP": 2.3, "INJ": 25, "FET": 2.2, "RENDER": 8,
            "SEI": 0.55, "TIA": 11, "JUP": 1.0, "WIF": 2.5, "BONK": 0.00002,
            "FLOKI": 0.00018, "SHIB": 0.000025, "CRO": 0.12, "SAND": 0.45,
            "MANA": 0.55, "AXS": 7.5, "GALA": 0.04, "ENJ": 0.35, "CHR": 0.3, "ALICE": 1.2
        }
        
        np.random.seed(hash(symbol) % 10000)
        length = 300 if interval == "1m" else 200
        
        base_price = MOCK_PRICES.get(symbol, 100.0)
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
        COOLDOWN = 3600  # 4 saat - aynı coin için bekle

        # Aynı coin + aynı yön → kesinlikle engelle
        if (new_signal.symbol == self.last_signal.symbol and 
            new_signal.signal == self.last_signal.signal):
            remaining = int(COOLDOWN - time_since)
            if remaining > 0:
                console.print(f"[#F97316]🚫 {new_signal.symbol} cooldown aktif ({remaining//60}d)[/#F97316]")
                return False

        # Genel cooldown - 4 saat
        if time_since < COOLDOWN:
            remaining = int(COOLDOWN - time_since)
            console.print(f"[#F97316]⏳ Cooldown aktif ({remaining//60}d)[/#F97316]")
            return False

        return True
    
    def _final_validation(self, signal: SignalResult) -> bool:
        """Sinyal gitmeden önce son doğrulama."""
        if signal.symbol not in self.kline_cache:
            return False
        
        df = self.kline_cache[signal.symbol]
        if df.empty or len(df) < 50:
            return False
        
        # Son bir kez daha evaluate et
        from .signals import evaluate_signal
        final_check = evaluate_signal(df, self.config, signal.symbol)
        
        # Sinyal yönü aynı olmalı
        if final_check.signal != signal.signal:
            return False
        
        # Confidence en az %5 olmalı
        if final_check.confidence < 5:
            return False
        
        return True
    
    def _send_telegram_notification(self, signal: SignalResult) -> None:
        """Send signal to Telegram channel if enabled."""
        if not self.config.telegram_enabled:
            console.print("[#F97316]⚠ Telegram devre dışı[/#F97316]")
            return
        
        # Dip buy sinyalleri için daha düşük eşik
        effective_min = self.config.telegram_min_confidence
        if signal.is_dip_buy:
            effective_min = effective_min * 0.8
        
        if signal.confidence < effective_min:
            console.print(f"[#F97316]⚠ Güvenilirlik düşük: {signal.confidence:.1f} < {effective_min:.1f}[/#F97316]")
            return
        
        if send_signal_notification is None:
            console.print("[#F97316]⚠ Telegram modülü bulunamadı - httpx yüklü mü?[/#F97316]")
            return
        
        try:
            success = send_signal_notification(
                bot_token=self.config.telegram_bot_token,
                channel_id=self.config.telegram_channel_id,
                symbol=signal.symbol,
                signal=signal.signal,
                entry_price=signal.entry_price,
                sl_price=signal.sl_price,
                tp_price=signal.tp3_price,
                leverage=signal.leverage,
                risk_reward=signal.risk_reward,
                confidence=signal.confidence,
                confidence_level=signal.confidence_level,
            )
            
            if success:
                console.print("[#10B981]✓ Telegram'a sinyal bildirimi gönderildi[/#10B981]")
            else:
                console.print("[#EF4444]✗ Telegram bildirimi başarısız - token/channel kontrol et[/#EF4444]")
        except Exception as e:
            console.print(f"[#EF4444]✗ Telegram hatası: {e}[/#EF4444]")
    
    def _send_telegram_top_coin(self, screened: List[Dict]) -> None:
        """Send only the top coin to Telegram with limit check."""
        if not self.config.telegram_enabled or not screened:
            return
        
        # Post limiti kontrolü
        now = time.time()
        
        # Gün sıfırlama (24 saat)
        if now - self.post_reset_time > 86400:
            self.posts_today = 0
            self.post_reset_time = now
        
        # Günlük limit
        if self.posts_today >= self.config.telegram_max_posts_per_day:
            console.print(f"[#F97316]⚠ Günlük post limiti dolu ({self.config.telegram_max_posts_per_day})[/#F97316]")
            return
        
        # Minimum aralık
        if now - self.last_post_time < self.config.telegram_min_interval_sec:
            remaining = int(self.config.telegram_min_interval_sec - (now - self.last_post_time))
            console.print(f"[#F97316]⏳ Post aralığı bekleniyor ({remaining}s)[/#F97316]")
            return
        
        best = screened[0]
        score = best.get("score", 0)
        
        # Score eşiği kontrolü
        if score < self.config.min_score:
            return
        
        # Gerekli verilerin tam olup olmadığını kontrol et
        symbol = best.get("symbol", "")
        signal_type = best.get("signal", "NONE")
        
        # Sinyal yönü net olmalı
        if signal_type not in ["LONG", "SHORT"]:
            return
        
        if not symbol or symbol not in self.kline_cache:
            return
        
        df = self.kline_cache[symbol]
        if df.empty or len(df) < 50:
            return
        
        current_price = float(df["close"].values[-1])
        prev_price = float(df["close"].values[-2])
        
        # Fiyat ve değişim hesapla
        price_change_24h = ((current_price - prev_price) / prev_price) * 100
        
        # SL/TP hesapla (yeni config değerleri ile)
        if signal_type == "LONG":
            sl_distance_pct = (self.config.long_sl_pct_min + self.config.long_sl_pct_max) / 2
            sl_price = current_price * (1 - sl_distance_pct / 100)
            tp1_price = current_price * (1 + self.config.long_tp1_pct / 100)
            tp2_price = current_price * (1 + self.config.long_tp2_pct / 100)
            tp3_price = current_price * (1 + self.config.long_tp3_pct / 100)
            leverage = self.config.long_leverage_min
        else:  # SHORT
            sl_distance_pct = (self.config.short_sl_pct_min + self.config.short_sl_pct_max) / 2
            sl_price = current_price * (1 + sl_distance_pct / 100)
            tp1_price = current_price * (1 - self.config.short_tp1_pct / 100)
            tp2_price = current_price * (1 - self.config.short_tp2_pct / 100)
            tp3_price = current_price * (1 - self.config.short_tp3_pct / 100)
            leverage = self.config.short_leverage_min
        
        try:
            from core.integrations.telegram import TelegramNotifier
            notifier = TelegramNotifier(self.config.telegram_bot_token, self.config.telegram_channel_id)
            
            # Order book analizi
            orderbook_data = None
            if self.config.orderbook_filter_enabled:
                from .orderbook import get_order_book_analysis
                ob = get_order_book_analysis(symbol, current_price)
                
                # Destek/direnç yoksa sinyal verme
                if self.config.require_support and not ob.strong_supports:
                    return
                if self.config.require_resistance and not ob.strong_resistances:
                    return
                
                orderbook_data = {
                    "supports": ob.strong_supports,
                    "resistances": ob.strong_resistances,
                    "imbalance": ob.imbalance,
                    "bid_ask_ratio": ob.bid_ask_ratio,
                }
            
            message = notifier.format_top_coin(
                symbol=symbol,
                score=score,
                rsi=best.get("rsi", 50),
                atr_pct=best.get("atr_pct", 0),
                vol_ratio=best.get("vol_ratio", 1),
                patterns=best.get("patterns", []),
                signal_type=signal_type,
                orderbook=orderbook_data,
                current_price=current_price,
                price_change=price_change_24h,
                sl_price=sl_price,
                tp1_price=tp1_price,
                tp2_price=tp2_price,
                tp3_price=tp3_price,
                leverage=leverage,
            )
            
            # Boş mesaj gönderme
            if not message:
                return
            
            import asyncio
            success = asyncio.run(notifier.send_message(message))
            
            if success:
                self.posts_today += 1
                self.last_post_time = now
                console.print(f"[#10B981]✓ Telegram'a gönderildi (Post {self.posts_today}/{self.config.telegram_max_posts_per_day})[/#10B981]")
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
        
        # Sadece en iyi 1 coini Telegram'a gönder
        self._send_telegram_top_coin(screened)

        # Sinyal üretimi
        signals = []
        for coin in screened[:self.config.max_signals_per_scan]:
            symbol = coin["symbol"]
            df = self.kline_cache[symbol]
            
            result: SignalResult = evaluate_signal(df, self.config, symbol=symbol)
            
            # Sinyal logla
            if self.trade_logger and result.signal != "NONE":
                self.trade_logger.log_signal({
                    "symbol": symbol,
                    "signal": result.signal,
                    "score": result.score,
                    "confidence": result.confidence,
                    "entry_price": result.entry_price,
                    "sl_price": result.sl_price,
                    "tp3_price": result.tp3_price,
                    "adx": result.adx,
                    "atr_ratio": result.atr_ratio,
                    "regime": result.regime_state,
                    "conditions": result.met_conditions,
                })
            
            if result.signal != "NONE" and result.confidence >= self.config.min_confidence:
                signals.append(result)

        # En iyi sinyali seç + confirmation
        if signals:
            signals.sort(key=lambda x: x.confidence, reverse=True)
            best = signals[0]
            
            # Brain ile final decision
            indicators = {
                "adx": best.adx,
                "rsi": best.indicators.get("rsi", 50),
                "ema_fast": best.indicators.get("ema_fast", 0),
                "ema_slow": best.indicators.get("ema_slow", 0),
                "volume_ratio": best.indicators.get("volume_ratio", 1),
                "atr": best.indicators.get("atr", 0),
                "atr_ratio": best.atr_ratio,
                "momentum": best.indicators.get("momentum", 0),
            }
            
            decision = self.brain.analyze(
                symbol=best.symbol,
                signal_result=best,
                regime=best.regime_state,
                indicators=indicators
            )
            
            # Brain kararı
            if decision.signal == "NONE":
                console.print(f"[#F97316]🧠 Brain REDDEDİ: {best.symbol} (Skor: {decision.final_score:.1f})[/#F97316]")
                return []
            
            # Final validation
            if not self._final_validation(best):
                console.print(f"[#F97316]🚫 {best.symbol} final validation başarısız[/#F97316]")
                return []
            
            if self.check_signal_confirmation(best):
                # Paper trading - pozisyon aç
                if self.paper_trader.can_open_position():
                    position = self.paper_trader.open_position(best)
                
                self.last_signal = best
                self.last_signal_time = time.time()
                self.signal_count += 1
                self._send_telegram_notification(best)
                
                signal_record = {
                    "timestamp": time.time(),
                    "symbol": best.symbol,
                    "signal": best.signal,
                    "confidence": best.confidence,
                    "regime": best.regime,
                    "is_dip_buy": best.is_dip_buy,
                    "entry_price": best.entry_price
                }
                self.signal_history.append(signal_record)
                
                if self.adaptive:
                    self.adaptive.record_signal(signal_record)
                
                return [best]
        
        # Açık pozisyonları güncelle
        self._update_open_positions()
        
        # Sinyal yoksa NinjaTrade modu
        self._ninja_trade_check(screened)
        
        scan_time = time.time() - start_time
        display_status_bar(self.signal_count, scan_time)
        
        return []
    
    def _update_open_positions(self) -> None:
        """Açık pozisyonları güncelle ve kapananları bildir."""
        # Fiyatları al
        prices = {}
        for symbol, df in self.kline_cache.items():
            if not df.empty:
                prices[symbol] = float(df["close"].values[-1])
        
        # Pozisyonları güncelle
        closed = self.paper_trader.update_positions(prices)
        
        # Kapanan pozisyonları Telegram'a bildir
        for pos in closed:
            self._send_trade_result(pos)
    
    def _send_trade_result(self, pos) -> None:
        """İşlem sonucunu Telegram'a gönder."""
        if not self.config.telegram_enabled:
            return
        
        try:
            from core.integrations.telegram import TelegramNotifier
            notifier = TelegramNotifier(self.config.telegram_bot_token, self.config.telegram_channel_id)
            
            emoji = "✅" if pos.is_profit else "❌"
            direction = "LONG" if pos.direction == "LONG" else "SHORT"
            
            message = f"""{emoji} <b>{direction} İŞLEM KAPATILDI • {pos.symbol}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Giriş:</b> ${pos.entry_price:.4f}
📊 <b>Çıkış:</b> ${pos.exit_price:.4f}
📈 <b>PnL:</b> {'+' if pos.pnl_pct >= 0 else ''}{pos.pnl_pct:.2f}% (${pos.pnl_usd:.2f})
🎯 <b>Sebep:</b> {pos.exit_reason}
⏱ <b>Süre:</b> {pos.duration/60:.0f} dakika
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 <b>Bakiye:</b> ${self.paper_trader.balance:,.2f}
📊 <b>Win Rate:</b> %{self.paper_trader.get_status()['win_rate']:.1f}
🔗 <a href="https://t.me/holygrailchat3301">HolyGrail</a>"""
            
            import asyncio
            asyncio.run(notifier.send_message(message))
        except Exception as e:
            console.print(f"[#EF4444]✗ Trade result hatası: {e}[/#EF4444]")

    def run(self):
        """Ana tarama döngüsü"""
        self.running = True
        display_banner()

        # ML modelini yükle veya eğit
        if self.config.ml_enabled:
            if not self.ml_engine.load("ml_model.pkl"):
                console.print("[#F59E0B]⚠ ML modeli bulunamadı, eğitiliyor...[/#F59E0B]")
                self.train_ml_models()
            else:
                self.ml_trained = True
                console.print("[#10B981]✓ ML modeli yüklendi[/#10B981]")

        console.print(Panel(
            f"[bold #00D4AA]⚡ SCANNER AKTİF - PRO SEVIYE[/bold #00D4AA]\n"
            f"[#6B7280]Coin Sayısı: {len(ALL_COINS)} • Interval: {self.config.scan_interval_sec}s\n"
            f"🧠 ML: {'AKTİF' if self.ml_trained else 'PASİF'} • "
            f"🌍 Regime: {'AKTİF' if self.config.regime_filter_enabled else 'PASİF'} • "
            f"📊 Exchange: MEXC[/#6B7280]",
            border_style="#334155",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

        try:
            while self.running:
                # Açık pozisyon varsa sadece güncelle, tarama yapma
                open_count = sum(1 for p in self.paper_trader.positions.values() if p.status == "OPEN")
                
                if open_count > 0:
                    # Açık pozisyonları güncelle
                    self._update_open_positions()
                    console.print(f"[#F59E0B]⏳ Açık pozisyon: {open_count} - Tarama bekleniyor...[/#F59E0B]")
                    time.sleep(30)  # 30 saniye bekle
                    continue
                
                # Yeni tarama
                signals = self.scan_once()
                if signals:
                    for sig in signals:
                        display_signal(sig)
                
                # Periyodik adaptif ayarlama
                self.scan_since_adapt += 1
                if self.adaptive and self.scan_since_adapt >= self.adapt_interval:
                    self._apply_adaptive_adjustments()
                    self.scan_since_adapt = 0
                
                time.sleep(self.config.scan_interval_sec)
                
        except KeyboardInterrupt:
            console.print("\n[bold #EF4444]🛑 Tarama durduruldu.[/bold #EF4444]")
            console.print(f"Toplam Tarama: {self.scan_count} | Toplam Sinyal: {self.signal_count}")
            if self.adaptive:
                console.print(self.adaptive.get_adaptive_summary())
            self.running = False
        except Exception as e:
            console.print(f"[#EF4444]Hata: {e}[/#EF4444]")
    
    def _apply_adaptive_adjustments(self) -> None:
        """Adaptif ayarlamaları uygula"""
        if not self.adaptive:
            return
        
        new_config = self.adaptive.apply_adjustments(self.config)
        
        # Değişiklikleri logla
        changes = []
        for f in self.config.__dataclass_fields__.values():
            old_val = getattr(self.config, f.name)
            new_val = getattr(new_config, f.name)
            if old_val != new_val:
                changes.append(f"{f.name}: {old_val} → {new_val}")
        
        if changes:
            console.print("[#3B82F6]🔄 Adaptif ayarlama yapıldı:[/#3B82F6]")
            for change in changes[:5]:  # Max 5 değişiklik göster
                console.print(f"  • {change}")
            
            self.config = new_config
            self.screener = MarketScreener(new_config)
    
    def _send_ninja_alert(self, symbol: str, event: str, price: float, change_pct: float, reason: str) -> None:
        """NinjaTrade uyarısı gönder."""
        if not self.config.telegram_enabled:
            return
        
        try:
            from core.integrations.telegram import TelegramNotifier
            notifier = TelegramNotifier(self.config.telegram_bot_token, self.config.telegram_channel_id)
            
            message = notifier.format_ninja_alert(
                symbol=symbol,
                event=event,
                price=price,
                change_pct=change_pct,
                reason=reason,
            )
            
            import asyncio
            asyncio.run(notifier.send_message(message))
        except Exception:
            pass
    
    def _is_already_tracked(self, symbol: str) -> bool:
        """Coin zaten takip listesinde mi?"""
        return symbol in self._tracked_coins
    
    def _add_to_tracking(self, symbol: str, direction: str, entry_price: float, reason: str) -> None:
        """Coin'i takip listesine ekle."""
        self._tracked_coins[symbol] = {
            "direction": direction,
            "entry_price": entry_price,
            "add_time": time.time(),
            "reason": reason,
            "alerts_sent": 1,
            "last_alert_time": time.time(),
        }
    
    def _update_tracking(self, symbol: str, current_price: float) -> Optional[str]:
        """Takip edilen coin'in durumunu güncelle. Return: status veya None."""
        if symbol not in self._tracked_coins:
            return None
        
        track = self._tracked_coins[symbol]
        entry_price = track["entry_price"]
        direction = track["direction"]
        
        # Kâr/zarar hesapla
        if direction == "LONG":
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100
        
        # Takip süresi
        track_duration = time.time() - track["add_time"]
        
        # Çıkış koşulları
        if pnl_pct < -2.0:
            return "STOP_LOSS"
        elif pnl_pct > 5.0:
            return "TAKE_PROFIT"
        elif track_duration > 3600 * 4:  # 4 saat sonra
            return "TIMEOUT"
        
        return None
    
    def _ninja_trade_check(self, screened: List[Dict]) -> None:
        """Akıllı NinjaTrade - İlk harekette uyarı ver, sonra izle."""
        if not self.config.ninja_trade_enabled:
            return
        
        # Takip listesindeki coinlerin durumunu kontrol et
        for symbol in list(self._tracked_coins.keys()):
            if symbol in self.kline_cache:
                df = self.kline_cache[symbol]
                if not df.empty:
                    current_price = float(df["close"].values[-1])
                    status = self._update_tracking(symbol, current_price)
                    
                    if status:
                        # Takipten çıkar
                        track = self._tracked_coins.pop(symbol)
                        
                        # Durum güncellemesi gönder
                        if status == "TAKE_PROFIT":
                            self._send_ninja_alert(
                                symbol=symbol,
                                event="TAKE_PROFIT HİT",
                                price=current_price,
                                change_pct=0,
                                reason=f"✅ Hedefe ulaşıldı! Giriş: ${track['entry_price']:.4f}"
                            )
                        elif status == "STOP_LOSS":
                            self._send_ninja_alert(
                                symbol=symbol,
                                event="STOP_LOSS HİT",
                                price=current_price,
                                change_pct=0,
                                reason=f"🛑 Stop loss çalıştı. Giriş: ${track['entry_price']:.4f}"
                            )
        
        # Yeni hareket kontrolü - sadece ilk seferde uyarı ver
        for coin in screened[:10]:
            symbol = coin.get("symbol", "")
            
            # Zaten takip listesindeyse atla
            if self._is_already_tracked(symbol):
                continue
            
            atr_pct = coin.get("atr_pct", 0)
            vol_ratio = coin.get("vol_ratio", 1)
            rsi = coin.get("rsi", 50)
            score = coin.get("score", 0)
            
            price_data = self.kline_cache.get(symbol)
            if price_data is None or price_data.empty:
                continue
            
            current_price = float(price_data["close"].values[-1])
            closes = price_data["close"].values
            
            # Son 5 mumdaki değişim
            if len(closes) >= 5:
                price_5_mum_ago = closes[-5]
                recent_change = (current_price - price_5_mum_ago) / price_5_mum_ago * 100
            else:
                recent_change = 0
            
            # SERT hareket tespiti (yeni kriterler)
            is_strong_move = False
            direction = "NEUTRAL"
            reason = ""
            
            # SHORT fırsatı - BTC gibi
            if recent_change < -1.5 and vol_ratio > 2.5 and rsi < 45:
                is_strong_move = True
                direction = "SHORT"
                reason = f"Sert düşüş: %{recent_change:.1f} | Vol: {vol_ratio:.1f}x | RSI: {rsi:.0f}"
            
            # LONG fırsatı
            elif recent_change > 1.5 and vol_ratio > 2.5 and rsi > 55:
                is_strong_move = True
                direction = "LONG"
                reason = f"Sert yükseliş: %{recent_change:.1f} | Vol: {vol_ratio:.1f}x | RSI: {rsi:.0f}"
            
            # Çok yüksek volatilite (tarafsız)
            elif atr_pct > 0.25 and vol_ratio > 4.0:
                is_strong_move = True
                direction = "WATCH"
                reason = f"Yüksek volatilite: ATR {atr_pct:.3f}% | Vol: {vol_ratio:.1f}x"
            
            if is_strong_move:
                # İlk uyarı
                self._send_ninja_alert(
                    symbol=symbol,
                    event=f"{direction} İZLEME ALINDI",
                    price=current_price,
                    change_pct=recent_change,
                    reason=reason
                )
                
                # Takip listesine ekle
                self._add_to_tracking(symbol, direction, current_price, reason)
                
                # Sadece 1 yeni coin ekle (spam önleme)
                break
