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

    # ATR - Daha stabil hesaplama
    atr_period: int = 7
    atr_min_pct: float = 0.12  # Minimum %0.12 volatilite

    # Volume
    volume_lookback: int = 14
    volume_spike_lookback: int = 5
    volume_spike_mult: float = 1.9

    # Trigger
    trigger_bps: float = 12.0

    # Risk - İyileştirilmiş SL/TP
    leverage: int = 5
    sl_atr_mult: float = 1.4   # Daha geniş SL (5x için)
    tp_atr_mult: float = 2.4   # Daha geniş TP (1:1.7+ hedef)
    min_risk_reward: float = 1.65  # Minimum R/R oranı

    # Signal requirements
    min_conditions: int = 5  # TÜM koşullar sağlanmalı (EMA+RSI+ATR+Volume+Trigger)
    min_confidence: float = 80.0  # Minimum %80 güvenilirlik
    min_score: int = 85  # Minimum sinyal skoru

    # Data
    min_data_length: int = 50

    # Scanner
    kline_interval: str = "1m"
    kline_limit: int = 250  # Daha fazla veri
    scan_interval_sec: int = 60
    top_pairs: int = 50
    max_signals_per_scan: int = 5
    price_refresh_sec: int = 1

    # Signal confirmation
    signal_cooldown_sec: int = 180  # 3 dakika cooldown
    confidence_diff_for_new_coin: float = 15.0  # Farklı coin için %15 fark

    # Telegram
    telegram_enabled: bool = True
    telegram_bot_token: str = "8346013289:AAHLbunkU_lSUTDDCcoVsOKbJxZ39TeMGXc"
    telegram_channel_id: str = "-1003561214306"
    telegram_min_confidence: float = 85.0

    @classmethod
    def from_dict(cls, d: dict) -> "ScalpConfig":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)
