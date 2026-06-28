import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from .config import ScalpConfig
from .indicators import TechnicalIndicators
from .patterns import full_candle_analysis, CandlePatterns
from .risk import RiskManager

@dataclass
class SignalResult:
    signal: str                    # "LONG", "SHORT", "NONE"
    symbol: str = ""
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    leverage: int = 5
    risk_reward: float = 0.0
    confidence: float = 0.0        # 0-100
    confidence_level: str = "DÜŞÜK"
    conditions: Dict[str, bool] = field(default_factory=dict)
    indicators: Dict[str, float] = field(default_factory=dict)
    condition_scores: Dict[str, float] = field(default_factory=dict)
    patterns: list = field(default_factory=list)

CONFIDENCE_WEIGHTS = {
    "ema_crossover": 28,
    "rsi_confirm": 18,
    "volume_spike": 22,
    "atr_volatility": 12,
    "momentum_trigger": 10,
    "candle_pattern": 10,
}

def calculate_confidence(scores: Dict[str, float]) -> Tuple[float, str]:
    """Ağırlıklı güven skoru hesaplama"""
    total = sum(scores.values())
    max_score = sum(CONFIDENCE_WEIGHTS.values())
    confidence = (total / max_score) * 100 if max_score > 0 else 0.0
    
    if confidence >= 85:
        level = "ÇOK YÜKSEK"
    elif confidence >= 72:
        level = "YÜKSEK"
    elif confidence >= 55:
        level = "ORTA"
    else:
        level = "DÜŞÜK"
    
    return round(confidence, 1), level


def evaluate_signal(df: pd.DataFrame, config: ScalpConfig, symbol: str = "") -> SignalResult:
    """Ana sinyal değerlendirme fonksiyonu"""
    result = SignalResult(signal="NONE", symbol=symbol)
    
    if len(df) < config.min_data_length:
        return result

    # Veriyi numpy array'e çevir
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values
    opens = df["open"].values

    # ==================== İNDİKATÖRLER ====================
    ind = TechnicalIndicators()
    
    ema_fast = ind.calc_ema(closes, config.ema_fast)
    ema_slow = ind.calc_ema(closes, config.ema_slow)
    rsi = ind.calc_rsi(closes, config.rsi_period)
    atr = ind.calc_atr(highs, lows, closes, config.atr_period)
    macd, macd_signal, macd_hist = ind.calc_macd(closes)
    
    is_vol_spike, vol_ratio = ind.calc_volume_spike(
        volumes, 
        config.volume_lookback, 
        config.volume_spike_lookback, 
        config.volume_spike_mult
    )

    current_price = float(closes[-1])
    prev_price = float(closes[-2])

    # ==================== PATTERN ANALİZ ====================
    pattern_analysis = full_candle_analysis(opens, highs, lows, closes, volumes)
    has_bullish_pattern = any(p in ["BULLISH_ENGULFING", "HAMMER", "STRONG_BULLISH"] 
                            for p in pattern_analysis["patterns"])
    has_bearish_pattern = any(p in ["BEARISH_ENGULFING", "SHOOTING_STAR", "STRONG_BEARISH"] 
                            for p in pattern_analysis["patterns"])

    # ==================== KOŞULLAR ====================
    # LONG
    long_ema = ind.check_crossover(ema_fast, ema_slow, "bullish")
    long_rsi = 30 < rsi[-1] < config.rsi_long_max if not np.isnan(rsi[-1]) else False
    long_vol = is_vol_spike
    long_momentum = current_price > prev_price * (1 + config.trigger_bps / 10000)
    long_pattern = has_bullish_pattern

    # SHORT
    short_ema = ind.check_crossover(ema_fast, ema_slow, "bearish")
    short_rsi = config.rsi_short_min < rsi[-1] < 70 if not np.isnan(rsi[-1]) else False
    short_vol = is_vol_spike
    short_momentum = current_price < prev_price * (1 - config.trigger_bps / 10000)
    short_pattern = has_bearish_pattern

    # ==================== CONFIDENCE SKORLARI ====================
    long_scores = {
        "ema_crossover": CONFIDENCE_WEIGHTS["ema_crossover"] if long_ema else 0,
        "rsi_confirm": CONFIDENCE_WEIGHTS["rsi_confirm"] if long_rsi else 0,
        "volume_spike": CONFIDENCE_WEIGHTS["volume_spike"] if long_vol else 0,
        "atr_volatility": CONFIDENCE_WEIGHTS["atr_volatility"] if atr[-1] > 0 else 0,
        "momentum_trigger": CONFIDENCE_WEIGHTS["momentum_trigger"] if long_momentum else 0,
        "candle_pattern": CONFIDENCE_WEIGHTS["candle_pattern"] if long_pattern else 0,
    }

    short_scores = {
        "ema_crossover": CONFIDENCE_WEIGHTS["ema_crossover"] if short_ema else 0,
        "rsi_confirm": CONFIDENCE_WEIGHTS["rsi_confirm"] if short_rsi else 0,
        "volume_spike": CONFIDENCE_WEIGHTS["volume_spike"] if short_vol else 0,
        "atr_volatility": CONFIDENCE_WEIGHTS["atr_volatility"] if atr[-1] > 0 else 0,
        "momentum_trigger": CONFIDENCE_WEIGHTS["momentum_trigger"] if short_momentum else 0,
        "candle_pattern": CONFIDENCE_WEIGHTS["candle_pattern"] if short_pattern else 0,
    }

    long_conf, long_level = calculate_confidence(long_scores)
    short_conf, short_level = calculate_confidence(short_scores)

    # ==================== SİNYAL KARARI ====================
    risk_manager = RiskManager(leverage=config.leverage)

    if (long_conf >= short_conf and 
        sum(long_scores.values()) > 0 and 
        long_conf >= config.min_confidence):
        
        atr_val = float(atr[-1])
        sl, tp = risk_manager.calculate_sl_tp(current_price, atr_val, "LONG",
                                            config.sl_atr_mult, config.tp_atr_mult)
        
        result.signal = "LONG"
        result.entry_price = current_price
        result.sl_price = sl
        result.tp_price = tp
        result.confidence = long_conf
        result.confidence_level = long_level
        result.conditions = {k: v > 0 for k, v in long_scores.items()}
        result.condition_scores = long_scores
        result.patterns = pattern_analysis["patterns"]

    elif (short_conf > long_conf and 
          sum(short_scores.values()) > 0 and 
          short_conf >= config.min_confidence):
        
        atr_val = float(atr[-1])
        sl, tp = risk_manager.calculate_sl_tp(current_price, atr_val, "SHORT",
                                            config.sl_atr_mult, config.tp_atr_mult)
        
        result.signal = "SHORT"
        result.entry_price = current_price
        result.sl_price = sl
        result.tp_price = tp
        result.confidence = short_conf
        result.confidence_level = short_level
        result.conditions = {k: v > 0 for k, v in short_scores.items()}
        result.condition_scores = short_scores
        result.patterns = pattern_analysis["patterns"]

    # Risk/Reward kontrolü
    if result.signal != "NONE":
        risk = abs(result.entry_price - result.sl_price)
        reward = abs(result.tp_price - result.entry_price)
        result.risk_reward = round(reward / risk, 2) if risk > 0 else 0.0
        
        # Minimum R/R kontrolü
        if result.risk_reward < config.min_risk_reward:
            result.signal = "NONE"
            return result
        
        # Minimum fiyat mesafesi kontrolleri
        sl_distance_pct = abs(result.entry_price - result.sl_price) / result.entry_price * 100
        tp_distance_pct = abs(result.tp_price - result.entry_price) / result.entry_price * 100
        
        if sl_distance_pct < config.min_sl_distance_pct:
            result.signal = "NONE"
            return result
        
        if tp_distance_pct < config.min_tp_distance_pct:
            result.signal = "NONE"
            return result
        
        # Momentum ve Volume zorunluluğu
        if config.require_momentum:
            if result.signal == "LONG" and not long_momentum:
                result.signal = "NONE"
                return result
            elif result.signal == "SHORT" and not short_momentum:
                result.signal = "NONE"
                return result
        
        if config.require_volume:
            if not is_vol_spike:
                result.signal = "NONE"
                return result

    return result
