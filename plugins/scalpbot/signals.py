import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional
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
    conditions: Dict[str, bool] = None
    indicators: Dict[str, float] = None

    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}
        if self.indicators is None:
            self.indicators = {}

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

    long_ema = check_crossover(ema_fast, ema_slow, "bullish")
    long_rsi = rsi[-1] < config.rsi_long_max if not np.isnan(rsi[-1]) else False
    long_atr = result.indicators["atr_pct"] > config.atr_min_pct
    long_vol = is_vol_spike
    long_trigger = current_price > prev_close * (1 + config.trigger_bps / 10000)

    short_ema = check_crossover(ema_fast, ema_slow, "bearish")
    short_rsi = rsi[-1] > config.rsi_short_min if not np.isnan(rsi[-1]) else False
    short_atr = long_atr
    short_vol = long_vol
    short_trigger = current_price < prev_close * (1 - config.trigger_bps / 10000)

    if long_ema and long_rsi and long_atr and long_vol and long_trigger:
        atr_val = atr[-1]
        result.signal = "LONG"
        result.entry_price = current_price
        result.sl_price = current_price - (atr_val * config.sl_atr_mult)
        result.tp_price = current_price + (atr_val * config.tp_atr_mult)
        result.conditions = {
            "ema_crossover": long_ema,
            "rsi_ok": long_rsi,
            "atr_ok": long_atr,
            "volume_spike": long_vol,
            "trigger_ok": long_trigger,
        }
    elif short_ema and short_rsi and short_atr and short_vol and short_trigger:
        atr_val = atr[-1]
        result.signal = "SHORT"
        result.entry_price = current_price
        result.sl_price = current_price + (atr_val * config.sl_atr_mult)
        result.tp_price = current_price - (atr_val * config.tp_atr_mult)
        result.conditions = {
            "ema_crossover": short_ema,
            "rsi_ok": short_rsi,
            "atr_ok": short_atr,
            "volume_spike": short_vol,
            "trigger_ok": short_trigger,
        }

    if result.signal != "NONE":
        risk = abs(result.entry_price - result.sl_price)
        reward = abs(result.tp_price - result.entry_price)
        result.risk_reward = reward / risk if risk > 0 else 0
        result.leverage = config.leverage

    return result
