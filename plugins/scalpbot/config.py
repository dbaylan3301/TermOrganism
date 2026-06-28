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

    # Risk - Sertleştirilmiş SL/TP
    leverage: int = 5
    sl_atr_mult: float = 0.9   # ATR * 0.9 (daha dar SL, hızlı çıkış)
    tp_atr_mult: float = 2.0   # ATR * 2.0 (1:2.2+ RR hedefi)
    min_risk_reward: float = 2.0  # Minimum 1:2 RR
    min_sl_distance_pct: float = 0.15  # Minimum %0.15 SL mesafesi
    min_tp_distance_pct: float = 0.30  # Minimum %0.30 TP mesafesi

    # Signal requirements - Sertleştirilmiş
    min_conditions: int = 6  # TÜM koşullar zorunlu (EMA+RSI+ATR+Volume+Trigger+Candle)
    min_confidence: float = 85.0  # Minimum %85 güvenilirlik
    min_score: int = 90  # Minimum sinyal skoru
    require_momentum: bool = True  # Momentum trigger zorunlu
    require_volume: bool = True  # Volume spike zorunlu

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
