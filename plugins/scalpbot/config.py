from dataclasses import dataclass

@dataclass
class ScalpConfig:
    # EMA
    ema_fast: int = 8
    ema_slow: int = 13

    # RSI
    rsi_period: int = 14
    rsi_long_max: float = 62.0
    rsi_short_min: float = 38.0

    # ATR
    atr_period: int = 7
    atr_min_pct: float = 0.18

    # Volume
    volume_lookback: int = 14
    volume_spike_lookback: int = 5
    volume_spike_mult: float = 1.9

    # Trigger
    trigger_bps: float = 12.0

    # Risk
    leverage: int = 5
    sl_atr_mult: float = 1.5
    tp_atr_mult: float = 1.7

    # Signal requirements - STRICT
    min_conditions: int = 4  # Minimum 4/5 koşul sağlanmalı
    min_confidence: float = 70.0  # Minimum %70 güvenilirlik

    # Scanner
    kline_interval: str = "1m"
    kline_limit: int = 200
    scan_interval_sec: int = 60
    top_pairs: int = 50
    price_refresh_sec: int = 1

    @classmethod
    def from_dict(cls, d: dict) -> "ScalpConfig":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)
