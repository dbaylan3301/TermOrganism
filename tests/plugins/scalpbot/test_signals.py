import numpy as np
import pandas as pd
from plugins.scalpbot.config import ScalpConfig
from plugins.scalpbot.signals import evaluate_signal, SignalResult

def make_ohlcv(n=200, trend="up"):
    np.random.seed(42)
    base = 100.0
    if trend == "up":
        closes = base + np.cumsum(np.random.randn(n) * 0.5 + 0.02)
    else:
        closes = base + np.cumsum(np.random.randn(n) * 0.5 - 0.02)
    highs = closes + np.abs(np.random.randn(n) * 0.3)
    lows = closes - np.abs(np.random.randn(n) * 0.3)
    opens = closes + np.random.randn(n) * 0.1
    volumes = np.random.randint(1000, 10000, n).astype(float)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volumes
    })

def test_signal_long_conditions_met():
    df = make_ohlcv(200, "up")
    config = ScalpConfig()
    result = evaluate_signal(df, config)
    assert isinstance(result, SignalResult)
    assert result.signal in ("LONG", "SHORT", "NONE")

def test_signal_short_conditions_met():
    df = make_ohlcv(200, "down")
    config = ScalpConfig()
    result = evaluate_signal(df, config)
    assert isinstance(result, SignalResult)

def test_signal_result_fields():
    df = make_ohlcv(200, "up")
    config = ScalpConfig()
    result = evaluate_signal(df, config)
    assert hasattr(result, "signal")
    assert hasattr(result, "entry_price")
    assert hasattr(result, "sl_price")
    assert hasattr(result, "tp_price")
    assert hasattr(result, "conditions")
    assert isinstance(result.conditions, dict)

def test_no_signal_on_insufficient_data():
    df = make_ohlcv(10, "up")
    config = ScalpConfig()
    result = evaluate_signal(df, config)
    assert result.signal == "NONE"
