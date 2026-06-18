from plugins.scalpbot.config import ScalpConfig

def test_default_config():
    config = ScalpConfig()
    assert config.ema_fast == 8
    assert config.ema_slow == 13
    assert config.rsi_period == 14
    assert config.rsi_long_max == 62
    assert config.rsi_short_min == 38
    assert config.atr_period == 7
    assert config.atr_min_pct == 0.18
    assert config.volume_lookback == 14
    assert config.volume_spike_mult == 1.9
    assert config.trigger_bps == 12
    assert config.leverage == 5
    assert config.sl_atr_mult == 1.5
    assert config.tp_atr_mult == 1.7

def test_config_from_dict():
    config = ScalpConfig.from_dict({"ema_fast": 10, "leverage": 10})
    assert config.ema_fast == 10
    assert config.leverage == 10
    assert config.ema_slow == 13  # default preserved