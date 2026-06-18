import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from .config import ScalpConfig
from .indicators import calc_ema, calc_rsi, calc_atr, calc_volume_spike, check_crossover

@dataclass
class SignalResult:
    signal: str  # "LONG", "SHORT", "NONE"
    symbol: str = ""
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp_price: float = 0.0
    leverage: int = 5
    risk_reward: float = 0.0
    confidence: float = 0.0  # 0-100%
    confidence_level: str = ""  # DÜŞÜK, ORTA, YÜKSEK, ÇOK YÜKSEK
    conditions: Dict[str, bool] = None
    indicators: Dict[str, float] = None
    condition_scores: Dict[str, float] = None

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}
        if self.indicators is None:
            self.indicators = {}
        if self.condition_scores is None:
            self.condition_scores = {}

CONFIDENCE_WEIGHTS = {
    "ema_crossover": 30,      # En önemli sinyal
    "rsi_confirm": 20,        # RSI onayı
    "atr_volatility": 15,     # Volatilite
    "volume_spike": 25,       # Hacim patlaması
    "trigger_momentum": 10,   # Fiyat momentumu
}

def calculate_confidence(scores: Dict[str, float]) -> Tuple[float, str]:
    """Calculate signal confidence based on weighted conditions."""
    total_score = sum(scores.values())
    max_possible = sum(CONFIDENCE_WEIGHTS.values())
    confidence = (total_score / max_possible) * 100 if max_possible > 0 else 0

    if confidence >= 85:
        level = "ÇOK YÜKSEK"
    elif confidence >= 70:
        level = "YÜKSEK"
    elif confidence >= 50:
        level = "ORTA"
    else:
        level = "DÜŞÜK"

    return confidence, level

def evaluate_signal(df: pd.DataFrame, config: ScalpConfig,
                    symbol: str = "") -> SignalResult:
    result = SignalResult(signal="NONE", symbol=symbol)

    if len(df) < config.kline_limit * 0.8:
        return result

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values

    ema_fast = calc_ema(closes, config.ema_fast)
    ema_slow = calc_ema(closes, config.ema_slow)
    rsi = calc_rsi(closes, config.rsi_period)
    atr = calc_atr(highs, lows, closes, config.atr_period)
    is_vol_spike, vol_ratio = calc_volume_spike(
        volumes, config.volume_lookback, config.volume_spike_lookback, config.volume_spike_mult
    )

    result.indicators = {
        "ema_fast": float(ema_fast[-1]) if not np.isnan(ema_fast[-1]) else 0,
        "ema_slow": float(ema_slow[-1]) if not np.isnan(ema_slow[-1]) else 0,
        "rsi": float(rsi[-1]) if not np.isnan(rsi[-1]) else 50,
        "atr": float(atr[-1]) if not np.isnan(atr[-1]) else 0,
        "atr_pct": float((atr[-1] / closes[-1]) * 100) if not np.isnan(atr[-1]) else 0,
        "vol_ratio": vol_ratio,
    }

    current_price = closes[-1]
    prev_close = closes[-2]

    # LONG conditions with scoring
    long_ema = check_crossover(ema_fast, ema_slow, "bullish")
    long_rsi = rsi[-1] < config.rsi_long_max if not np.isnan(rsi[-1]) else False
    long_atr = result.indicators["atr_pct"] > config.atr_min_pct
    long_vol = is_vol_spike
    long_trigger = current_price > prev_close * (1 + config.trigger_bps / 10000)

    # SHORT conditions with scoring
    short_ema = check_crossover(ema_fast, ema_slow, "bearish")
    short_rsi = rsi[-1] > config.rsi_short_min if not np.isnan(rsi[-1]) else False
    short_atr = long_atr
    short_vol = long_vol
    short_trigger = current_price < prev_close * (1 - config.trigger_bps / 10000)

    # Calculate LONG confidence
    long_scores = {
        "ema_crossover": CONFIDENCE_WEIGHTS["ema_crossover"] if long_ema else 0,
        "rsi_confirm": CONFIDENCE_WEIGHTS["rsi_confirm"] if long_rsi else 0,
        "atr_volatility": CONFIDENCE_WEIGHTS["atr_volatility"] if long_atr else 0,
        "volume_spike": CONFIDENCE_WEIGHTS["volume_spike"] if long_vol else 0,
        "trigger_momentum": CONFIDENCE_WEIGHTS["trigger_momentum"] if long_trigger else 0,
    }
    long_confidence, long_level = calculate_confidence(long_scores)

    # Calculate SHORT confidence
    short_scores = {
        "ema_crossover": CONFIDENCE_WEIGHTS["ema_crossover"] if short_ema else 0,
        "rsi_confirm": CONFIDENCE_WEIGHTS["rsi_confirm"] if short_rsi else 0,
        "atr_volatility": CONFIDENCE_WEIGHTS["atr_volatility"] if short_atr else 0,
        "volume_spike": CONFIDENCE_WEIGHTS["volume_spike"] if short_vol else 0,
        "trigger_momentum": CONFIDENCE_WEIGHTS["trigger_momentum"] if short_trigger else 0,
    }
    short_confidence, short_level = calculate_confidence(short_scores)

    # Select best signal - REQUIRE MINIMUM 4 CONDITIONS
    long_conditions_met = sum([long_ema, long_rsi, long_atr, long_vol, long_trigger])
    short_conditions_met = sum([short_ema, short_rsi, short_atr, short_vol, short_trigger])

    MIN_CONDITIONS = 4  # Minimum 4 koşul sağlanmalı
    MIN_CONFIDENCE = 70  # Minimum %70 güvenilirlik

    if (long_confidence >= short_confidence and long_conditions_met >= MIN_CONDITIONS
        and long_confidence >= MIN_CONFIDENCE):
        atr_val = atr[-1]
        result.signal = "LONG"
        result.entry_price = current_price
        result.sl_price = current_price - (atr_val * config.sl_atr_mult)
        result.tp_price = current_price + (atr_val * config.tp_atr_mult)
        result.confidence = long_confidence
        result.confidence_level = long_level
        result.conditions = {
            "ema_crossover": long_ema,
            "rsi_ok": long_rsi,
            "atr_ok": long_atr,
            "volume_spike": long_vol,
            "trigger_ok": long_trigger,
        }
        result.condition_scores = long_scores
    elif (short_confidence > long_confidence and short_conditions_met >= MIN_CONDITIONS
          and short_confidence >= MIN_CONFIDENCE):
        atr_val = atr[-1]
        result.signal = "SHORT"
        result.entry_price = current_price
        result.sl_price = current_price + (atr_val * config.sl_atr_mult)
        result.tp_price = current_price - (atr_val * config.tp_atr_mult)
        result.confidence = short_confidence
        result.confidence_level = short_level
        result.conditions = {
            "ema_crossover": short_ema,
            "rsi_ok": short_rsi,
            "atr_ok": short_atr,
            "volume_spike": short_vol,
            "trigger_ok": short_trigger,
        }
        result.condition_scores = short_scores

    if result.signal != "NONE":
        risk = abs(result.entry_price - result.sl_price)
        reward = abs(result.tp_price - result.entry_price)
        result.risk_reward = reward / risk if risk > 0 else 0
        result.leverage = config.leverage

    return result
