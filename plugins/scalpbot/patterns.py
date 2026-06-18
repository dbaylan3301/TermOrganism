import numpy as np
from typing import Dict, List, Tuple
from .config import ScalpConfig

def detect_doji(open: float, high: float, low: float, close: float) -> bool:
    body = abs(close - open)
    total = high - low
    if total == 0:
        return False
    return body / total < 0.1

def detect_hammer(open: float, high: float, low: float, close: float) -> bool:
    body = abs(close - open)
    lower_shadow = min(open, close) - low
    upper_shadow = high - max(open, close)
    if body == 0:
        return False
    return lower_shadow > body * 2 and upper_shadow < body * 0.5

def detect_engulfing(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> str:
    if len(opens) < 2:
        return "NONE"
    prev_open, prev_close = opens[-2], closes[-2]
    curr_open, curr_close = opens[-1], closes[-1]
    prev_body = prev_close - prev_open
    curr_body = curr_close - curr_open
    if prev_body < 0 and curr_body > 0 and curr_close > prev_open and curr_open < prev_close:
        return "BULLISH_ENGULFING"
    elif prev_body > 0 and curr_body < 0 and curr_close < prev_open and curr_open > prev_close:
        return "BEARISH_ENGULFING"
    return "NONE"

def detect_momentum_candles(closes: np.ndarray, period: int = 3) -> str:
    if len(closes) < period + 1:
        return "NONE"
    recent = closes[-period:]
    changes = np.diff(recent)
    if all(c > 0 for c in changes):
        return "STRONG_UPTREND"
    elif all(c < 0 for c in changes):
        return "STRONG_DOWNTREND"
    return "NONE"

def analyze_volume_profile(volumes: np.ndarray, closes: np.ndarray) -> Dict:
    if len(volumes) < 20:
        return {"trend": "NEUTRAL", "accumulation": False, "distribution": False}
    vol_ma20 = np.mean(volumes[-20:])
    vol_ma5 = np.mean(volumes[-5:])
    price_trend = closes[-1] - closes[-5]
    vol_trend = vol_ma5 - vol_ma20
    accumulation = vol_trend > 0 and price_trend > 0
    distribution = vol_trend > 0 and price_trend < 0
    return {
        "trend": "INCREASING" if vol_trend > 0 else "DECREASING",
        "accumulation": accumulation,
        "distribution": distribution,
        "vol_ratio": vol_ma5 / vol_ma20 if vol_ma20 > 0 else 1.0
    }

def calculate_support_resistance(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Dict:
    if len(highs) < 20:
        return {"support": 0, "resistance": 0, "distance_pct": 0}
    recent_highs = highs[-50:] if len(highs) >= 50 else highs
    recent_lows = lows[-50:] if len(lows) >= 50 else lows
    resistance = np.percentile(recent_highs, 90)
    support = np.percentile(recent_lows, 10)
    current = closes[-1]
    dist_to_resistance = (resistance - current) / current * 100
    dist_to_support = (current - support) / current * 100
    return {
        "support": support,
        "resistance": resistance,
        "dist_to_resistance": dist_to_resistance,
        "dist_to_support": dist_to_support,
        "position": "NEAR_RESISTANCE" if dist_to_resistance < 1 else "NEAR_SUPPORT" if dist_to_support < 1 else "MIDDLE"
    }

def multi_timeframe_score(indicators_1m: Dict, indicators_5m: Dict, indicators_15m: Dict, indicators_1h: Dict) -> float:
    score = 0
    timeframes = [
        ("1m", indicators_1m, 0.15),
        ("5m", indicators_5m, 0.25),
        ("15m", indicators_15m, 0.30),
        ("1h", indicators_1h, 0.30),
    ]
    for tf, ind, weight in timeframes:
        if not ind:
            continue
        rsi = ind.get("rsi", 50)
        ema_diff = ind.get("ema_diff", 0)
        if 40 <= rsi <= 60:
            score += weight * 50
        elif 35 <= rsi <= 65:
            score += weight * 30
        if abs(ema_diff) < 0.1:
            score += weight * 50
        elif abs(ema_diff) < 0.3:
            score += weight * 30
    return score

def full_analysis(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                  closes: np.ndarray, volumes: np.ndarray) -> Dict:
    patterns = []
    doji = detect_doji(opens[-1], highs[-1], lows[-1], closes[-1])
    if doji:
        patterns.append("DOJI")
    hammer = detect_hammer(opens[-1], highs[-1], lows[-1], closes[-1])
    if hammer:
        patterns.append("HAMMER")
    engulfing = detect_engulfing(opens, highs, lows, closes)
    if engulfing != "NONE":
        patterns.append(engulfing)
    momentum = detect_momentum_candles(closes)
    if momentum != "NONE":
        patterns.append(momentum)
    volume_profile = analyze_volume_profile(volumes, closes)
    sr_levels = calculate_support_resistance(highs, lows, closes)
    return {
        "patterns": patterns,
        "pattern_count": len(patterns),
        "volume_profile": volume_profile,
        "support_resistance": sr_levels,
        "trend_strength": abs(closes[-1] - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0,
    }
