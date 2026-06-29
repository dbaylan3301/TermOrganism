from dataclasses import dataclass, field
from typing import Dict, Optional
import json
import os

@dataclass
class ScalpConfig:
    # ==================== GENEL ====================
    ema_fast: int = 6
    ema_slow: int = 21
    ema_cross_threshold: float = 9.0
    rsi_period: int = 14
    atr_period: int = 14
    atr_min_pct: float = 0.12
    momentum_period: int = 10
    candle_period: int = 8
    min_data_length: int = 50
    leverage: int = 5
    min_risk_reward: float = 2.8
    max_risk_per_trade: float = 1.5
    min_score: int = 75  # gevşetildi
    min_confidence: float = 75.0  # gevşetildi
    min_conditions: int = 4  # gevşetildi - 4/6 yeterli
    require_ema_confirm: bool = True
    require_volume: bool = True
    require_candle_pattern: bool = True
    require_orderbook: bool = True

    # ==================== LONG ====================
    long_ema_cross_threshold: float = 9.0
    long_rsi_min: float = 48.0
    long_rsi_max: float = 70.0
    long_atr_ratio_min: float = 1.55
    long_volume_mult: float = 2.5
    long_momentum_min: float = 20.0
    long_candle_bullish_ratio: float = 0.62
    long_sl_pct_min: float = 1.0
    long_sl_pct_max: float = 1.4
    long_tp1_pct: float = 2.2
    long_tp2_pct: float = 4.5
    long_tp3_pct: float = 7.5
    long_leverage_min: int = 4
    long_leverage_max: int = 7
    long_score_ema: int = 18
    long_score_rsi: int = 16
    long_score_volume: int = 17
    long_score_atr: int = 15
    long_score_momentum: int = 16
    long_score_candle: int = 15

    # ==================== SHORT ====================
    short_ema_cross_threshold: float = 9.0
    short_rsi_max: float = 50.0  # 50'in altında short imkanı
    short_rsi_overbought: float = 70.0
    short_atr_ratio_min: float = 1.2
    short_volume_mult: float = 2.0
    short_momentum_max: float = -3.0  # Negatif momentum zorunlu
    short_candle_bearish_ratio: float = 0.55
    short_sl_pct_min: float = 1.1
    short_sl_pct_max: float = 1.6
    short_tp1_pct: float = 2.0
    short_tp2_pct: float = 4.0
    short_tp3_pct: float = 7.0
    short_leverage_min: int = 5
    short_leverage_max: int = 8
    short_score_ema: int = 18
    short_score_rsi: int = 18
    short_score_volume: int = 18
    short_score_atr: int = 16
    short_score_momentum: int = 17
    short_score_candle: int = 16

    # ==================== BONUS ====================
    bonus_higher_low: int = 20
    bonus_lower_high: int = 20
    bonus_orderbook: int = 10

    # ==================== TREND / VOLUME / TIME ====================
    trend_filter_enabled: bool = True
    trend_filter_ema_period: int = 200
    volume_lookback: int = 14
    volume_spike_lookback: int = 5
    volume_spike_mult: float = 2.8
    volume_condition_enabled: bool = True
    volume_condition_lookback: int = 5
    volume_condition_mult: float = 1.8
    time_filter_enabled: bool = True
    time_filter_start_hour: int = 8
    time_filter_end_hour: int = 20

    # ==================== ORDER BOOK ====================
    orderbook_filter_enabled: bool = True
    orderbook_min_imbalance: float = 0.3
    orderbook_min_bid_ask: float = 1.3
    require_support: bool = True
    require_resistance: bool = True

    # ==================== RISK ====================
    min_sl_distance_pct: float = 0.18
    max_sl_distance_pct: float = 0.22
    signal_cooldown_sec: int = 14400

    # ==================== REGIME ====================
    regime_adx_period: int = 14
    regime_adx_threshold: float = 20.0
    regime_atr_ratio_threshold: float = 1.2
    regime_filter_enabled: bool = True
    regime_detection_enabled: bool = True
    regime_lookback_periods: int = 50
    regime_drop_threshold_pct: float = 4.0
    regime_oversold_rsi: float = 30.0
    regime_trend_strength_threshold: float = 0.3

    # ==================== DİNAMİK SL/TP ====================
    dynamic_sl_enabled: bool = True
    sl_atr_multiplier: float = 1.8

    # ==================== TELEGRAM ====================
    telegram_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""
    telegram_min_confidence: float = 85.0
    telegram_max_posts_per_day: int = 3
    telegram_min_interval_sec: int = 3600

    # ==================== SCANNER ====================
    kline_limit: int = 250
    scan_interval_sec: int = 60
    top_pairs: int = 50
    max_signals_per_scan: int = 5

    # ==================== NINJA ====================
    ninja_trade_enabled: bool = True

    # ==================== ML ====================
    ml_enabled: bool = True
    ml_confidence_threshold: float = 60.0

    # ==================== AI ====================
    ai_enabled: bool = True
    ai_confidence_threshold: float = 0.65

    # ==================== ADAPTIVE ====================
    adaptive_enabled: bool = True
    adaptive_win_rate_target: float = 0.55
    adaptive_lookback_signals: int = 20
    adaptive_adjustment_rate: float = 0.1

    # ==================== WFO ====================
    wfo_in_sample_pct: float = 0.70
    wfo_min_forward_days: int = 90
    wfo_min_sharpe: float = 1.2
    wfo_min_profit_factor: float = 1.6

    # ==================== RISK MGMT ====================
    max_drawdown_pct: float = 12.0
    slippage_bps: float = 6.0
    funding_rate_daily: float = 0.01

    # ==================== LOGGING ====================
    logging_enabled: bool = True
    log_dir: str = "logs"

    # ==================== PERSISTENCE ====================
    config_file: str = field(default_factory=lambda: "")

    @classmethod
    def from_dict(cls, d: dict) -> "ScalpConfig":
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    def save_to_file(self, path: str = "") -> None:
        save_path = path or self.config_file or "scalp_config.json"
        data = {}
        for f in self.__dataclass_fields__():
            val = getattr(self, f.name)
            if not f.name.startswith('_'):
                data[f.name] = val
        with open(save_path, 'w') as fp:
            json.dump(data, fp, indent=2)

    @classmethod
    def load_from_file(cls, path: str = "scalp_config.json") -> "ScalpConfig":
        if os.path.exists(path):
            with open(path, 'r') as fp:
                data = json.load(fp)
            return cls.from_dict(data)
        return cls()
