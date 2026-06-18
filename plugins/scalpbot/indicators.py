import numpy as np
from typing import Tuple

def calc_ema(prices: np.ndarray, period: int) -> np.ndarray:
    ema = np.full_like(prices, np.nan, dtype=float)
    if len(prices) < period:
        return ema
    ema[period - 1] = np.mean(prices[:period])
    multiplier = 2.0 / (period + 1)
    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema

def calc_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    rsi = np.full_like(prices, np.nan, dtype=float)
    if len(prices) < period + 1:
        return rsi
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
             period: int = 7) -> np.ndarray:
    atr = np.full_like(highs, np.nan, dtype=float)
    if len(highs) < period + 1:
        return atr
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    atr[period] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
    return atr

def calc_volume_spike(volumes: np.ndarray, lookback: int = 14,
                      spike_lookback: int = 5, mult: float = 1.9) -> Tuple[bool, float]:
    if len(volumes) < lookback + spike_lookback:
        return False, 0.0
    recent_avg = np.mean(volumes[-spike_lookback:])
    lookback_avg = np.mean(volumes[-(lookback + spike_lookback):-spike_lookback])
    if lookback_avg == 0:
        return False, 0.0
    ratio = recent_avg / lookback_avg
    return bool(ratio >= mult), ratio

def check_crossover(ema_fast: np.ndarray, ema_slow: np.ndarray,
                    direction: str = "bullish") -> bool:
    if len(ema_fast) < 2 or len(ema_slow) < 2:
        return False
    if np.isnan(ema_fast[-1]) or np.isnan(ema_slow[-1]):
        return False
    if np.isnan(ema_fast[-2]) or np.isnan(ema_slow[-2]):
        return False
    if direction == "bullish":
        return ema_fast[-2] <= ema_slow[-2] and ema_fast[-1] > ema_slow[-1]
    elif direction == "bearish":
        return ema_fast[-2] >= ema_slow[-2] and ema_fast[-1] < ema_slow[-1]
    return False
