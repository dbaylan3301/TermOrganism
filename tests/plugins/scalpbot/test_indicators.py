import numpy as np
import pandas as pd
from plugins.scalpbot.indicators import (
    calc_ema, calc_rsi, calc_atr, calc_volume_spike, check_crossover
)

def test_calc_ema():
    prices = np.arange(1.0, 30.0, 0.5)
    ema = calc_ema(prices, period=8)
    assert len(ema) == len(prices)
    assert ema[-1] > ema[-2]
    assert np.isnan(ema[0])

def test_calc_rsi():
    np.random.seed(42)
    prices = np.cumsum(np.random.randn(100)) + 100
    rsi = calc_rsi(prices, period=14)
    assert len(rsi) == len(prices)
    assert 0 <= rsi[-1] <= 100
    assert np.isnan(rsi[12])

def test_calc_atr():
    highs = np.arange(102.0, 122.0, 1.0)
    lows = np.arange(100.0, 120.0, 1.0)
    closes = np.arange(101.0, 121.0, 1.0)
    atr = calc_atr(highs, lows, closes, period=7)
    assert len(atr) == len(highs)
    assert atr[-1] > 0

def test_calc_atr_pct():
    n = 20
    highs = np.linspace(100, 110, n) + np.random.default_rng(42).normal(0, 0.5, n)
    lows = highs - 3.0
    closes = highs - 1.5
    atr = calc_atr(highs, lows, closes, period=2)
    valid = atr[~np.isnan(atr)]
    assert len(valid) > 0
    atr_pct = (atr / closes) * 100
    valid_pct = atr_pct[~np.isnan(atr_pct)]
    assert len(valid_pct) > 0
    assert valid_pct[-1] > 0

def test_calc_volume_spike():
    volumes = np.array([100, 120, 110, 130, 105,
                        80, 90, 85, 95, 70, 88, 92, 78, 85,
                        75, 80, 70, 85, 90, 95, 88, 82, 77, 83, 89, 91, 86, 84])
    is_spike, ratio = calc_volume_spike(volumes, lookback=14, spike_lookback=5, mult=1.9)
    assert isinstance(is_spike, bool)
    assert ratio > 0

def test_check_crossover_bullish():
    ema_fast = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    ema_slow = np.array([12.0, 12.5, 12.8, 13.5, 13.0])
    assert check_crossover(ema_fast, ema_slow, direction="bullish") == True

def test_check_crossover_bearish():
    ema_fast = np.array([14.0, 13.0, 13.5, 11.0, 10.0])
    ema_slow = np.array([12.0, 12.5, 10.8, 10.5, 12.0])
    assert check_crossover(ema_fast, ema_slow, direction="bearish") == True

def test_check_crossover_none():
    ema_fast = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    ema_slow = np.array([9.0, 10.0, 11.0, 12.0, 13.0])
    assert check_crossover(ema_fast, ema_slow, direction="bullish") == False
    assert check_crossover(ema_fast, ema_slow, direction="bearish") == False
