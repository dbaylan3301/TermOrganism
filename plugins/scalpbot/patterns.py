import numpy as np
from typing import Dict, List, Tuple
from .indicators import TechnicalIndicators

class CandlePatterns:
    """Mum formasyonları ve pattern detection."""

    @staticmethod
    def detect_doji(open_price: float, high: float, low: float, close: float,
                    body_ratio: float = 0.1) -> bool:
        """Doji - Çok küçük body"""
        body = abs(close - open_price)
        total_range = high - low
        if total_range == 0:
            return False
        return body / total_range <= body_ratio

    @staticmethod
    def detect_hammer(open_price: float, high: float, low: float, close: float,
                      body_mult: float = 2.0, shadow_mult: float = 0.5) -> bool:
        """Hammer / Inverted Hammer"""
        body = abs(close - open_price)
        lower_shadow = min(open_price, close) - low
        upper_shadow = high - max(open_price, close)
        
        if body == 0:
            return False
        return (lower_shadow >= body * body_mult and 
                upper_shadow <= body * shadow_mult)

    @staticmethod
    def detect_shooting_star(open_price: float, high: float, low: float, close: float) -> bool:
        """Shooting Star"""
        body = abs(close - open_price)
        lower_shadow = min(open_price, close) - low
        upper_shadow = high - max(open_price, close)
        
        if body == 0:
            return False
        return (upper_shadow >= body * 2.0 and 
                lower_shadow <= body * 0.5)

    @staticmethod
    def detect_engulfing(opens: np.ndarray, highs: np.ndarray,
                        lows: np.ndarray, closes: np.ndarray) -> str:
        """Bullish / Bearish Engulfing"""
        if len(opens) < 2:
            return "NONE"
        
        prev_o, prev_c = opens[-2], closes[-2]
        curr_o, curr_c = opens[-1], closes[-1]
        
        prev_body = prev_c - prev_o
        curr_body = curr_c - curr_o
        
        # Bullish Engulfing
        if (prev_body < 0 and curr_body > 0 and 
            curr_c > prev_o and curr_o < prev_c):
            return "BULLISH_ENGULFING"
        
        # Bearish Engulfing
        if (prev_body > 0 and curr_body < 0 and 
            curr_c < prev_o and curr_o > prev_c):
            return "BEARISH_ENGULFING"
        
        return "NONE"

    @staticmethod
    def detect_momentum_candles(closes: np.ndarray, period: int = 3) -> str:
        """Kısa süreli güçlü trend"""
        if len(closes) < period + 1:
            return "NONE"
        
        recent = closes[-period:]
        changes = np.diff(recent)
        
        if all(c > 0 for c in changes):
            return "STRONG_BULLISH"
        elif all(c < 0 for c in changes):
            return "STRONG_BEARISH"
        return "NONE"

    @staticmethod
    def analyze_volume_profile(volumes: np.ndarray, closes: np.ndarray,
                              lookback: int = 20) -> Dict:
        """Volume analizi"""
        if len(volumes) < lookback:
            return {"trend": "NEUTRAL", "accumulation": False, 
                   "distribution": False, "vol_ratio": 1.0}
        
        vol_ma_long = np.mean(volumes[-lookback:])
        vol_ma_short = np.mean(volumes[-5:])
        price_change = closes[-1] - closes[-5] if len(closes) >= 5 else 0
        
        vol_increasing = vol_ma_short > vol_ma_long * 1.1
        
        accumulation = vol_increasing and price_change > 0
        distribution = vol_increasing and price_change < 0
        
        return {
            "trend": "INCREASING" if vol_increasing else "DECREASING",
            "accumulation": accumulation,
            "distribution": distribution,
            "vol_ratio": vol_ma_short / vol_ma_long if vol_ma_long > 0 else 1.0,
            "volume_spike": TechnicalIndicators.calc_volume_spike(volumes)[0]
        }

    @staticmethod
    def calculate_support_resistance(highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, lookback: int = 50) -> Dict:
        """Destek ve Direnç Seviyeleri"""
        if len(highs) < 20:
            return {"support": 0.0, "resistance": 0.0, "position": "NEUTRAL"}
        
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        resistance = np.percentile(recent_highs, 92)
        support = np.percentile(recent_lows, 8)
        current = closes[-1]
        
        dist_res = (resistance - current) / current * 100
        dist_sup = (current - support) / current * 100
        
        position = "NEAR_RESISTANCE" if dist_res < 1.5 else \
                   "NEAR_SUPPORT" if dist_sup < 1.5 else "MIDDLE"
        
        return {
            "support": float(support),
            "resistance": float(resistance),
            "dist_to_resistance": float(dist_res),
            "dist_to_support": float(dist_sup),
            "position": position
        }


def full_candle_analysis(opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, volumes: np.ndarray) -> Dict:
    """Tek fonksiyonda kapsamlı mum + volume + SR analizi"""
    patterns: List[str] = []
    
    # Tek mum pattern'leri
    if CandlePatterns.detect_doji(opens[-1], highs[-1], lows[-1], closes[-1]):
        patterns.append("DOJI")
    if CandlePatterns.detect_hammer(opens[-1], highs[-1], lows[-1], closes[-1]):
        patterns.append("HAMMER")
    if CandlePatterns.detect_shooting_star(opens[-1], highs[-1], lows[-1], closes[-1]):
        patterns.append("SHOOTING_STAR")
    
    # İki mum pattern
    engulfing = CandlePatterns.detect_engulfing(opens, highs, lows, closes)
    if engulfing != "NONE":
        patterns.append(engulfing)
    
    # Momentum
    momentum = CandlePatterns.detect_momentum_candles(closes)
    if momentum != "NONE":
        patterns.append(momentum)
    
    volume_profile = CandlePatterns.analyze_volume_profile(volumes, closes)
    sr_levels = CandlePatterns.calculate_support_resistance(highs, lows, closes)
    
    return {
        "patterns": patterns,
        "pattern_count": len(patterns),
        "volume_profile": volume_profile,
        "support_resistance": sr_levels,
        "trend_strength": abs(closes[-1] - closes[-20]) / closes[-20] * 100 
                         if len(closes) >= 20 else 0.0,
        "last_price": float(closes[-1])
    }


# İleride multi-timeframe için
def multi_timeframe_score(indicators_by_tf: Dict[str, Dict]) -> float:
    """Çoklu zaman dilimi uyum skoru"""
    weights = {"1m": 0.15, "5m": 0.20, "15m": 0.25, "1h": 0.40}
    score = 0.0
    
    for tf, ind in indicators_by_tf.items():
        weight = weights.get(tf, 0.2)
        rsi = ind.get("rsi", 50)
        ema_fast = ind.get("ema_fast", 0)
        ema_slow = ind.get("ema_slow", 0)
        macd_hist = ind.get("macd_hist", 0)
        
        # RSI nötr bölgede ise bonus
        if 40 <= rsi <= 60:
            score += weight * 45
        elif 30 <= rsi <= 70:
            score += weight * 25
        
        # EMA ve MACD uyumu
        if abs(ema_fast - ema_slow) < 0.2:
            score += weight * 30
        if macd_hist > 0:
            score += weight * 20
    
    return min(score, 100.0)
