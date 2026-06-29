import numpy as np
import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from .config import ScalpConfig
from .indicators import TechnicalIndicators
from .patterns import full_candle_analysis, CandlePatterns
from .risk import RiskManager
from .orderbook import get_order_book_analysis, OrderBookAnalysis
from .regime import RegimeDetector, RegimeState
from .ml_engine import MLEnsemble, MLPrediction

@dataclass
class SignalResult:
    signal: str                    # "LONG", "SHORT", "NONE"
    symbol: str = ""
    entry_price: float = 0.0
    sl_price: float = 0.0
    tp1_price: float = 0.0
    tp2_price: float = 0.0
    tp3_price: float = 0.0
    leverage: int = 5
    risk_reward: float = 0.0
    confidence: float = 0.0        # 0-100
    confidence_level: str = "DÜŞÜK"
    conditions: Dict[str, bool] = field(default_factory=dict)
    indicators: Dict[str, float] = field(default_factory=dict)
    condition_scores: Dict[str, float] = field(default_factory=dict)
    patterns: list = field(default_factory=list)
    regime: str = "NEUTRAL"
    is_dip_buy: bool = False
    score: int = 0
    met_conditions: int = 0
    # Yeni alanlar
    adx: float = 0.0
    atr_ratio: float = 1.0
    regime_state: str = "UNKNOWN"
    is_tradeable: bool = True
    validation_passed: bool = False
    # ML
    ml_direction: str = "NEUTRAL"
    ml_confidence: float = 0.0
    ml_prob_long: float = 0.0
    ml_prob_short: float = 0.0

# Eski ağırlıklar (uyumluluk için)
CONFIDENCE_WEIGHTS = {
    "ema_crossover": 25,
    "rsi_confirm": 18,
    "volume_spike": 20,
    "atr_volatility": 12,
    "momentum_trigger": 15,
    "candle_pattern": 10,
}

CONFIDENCE_WEIGHTS = {
    "ema_crossover": 25,
    "rsi_confirm": 18,
    "volume_spike": 20,
    "atr_volatility": 12,
    "momentum_trigger": 15,
    "candle_pattern": 10,
}

@dataclass
class RegimeInfo:
    regime: str = "NEUTRAL"  # TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE
    trend_strength: float = 0.0
    recent_change_pct: float = 0.0
    is_oversold: bool = False
    is_overbought: bool = False
    support_level: float = 0.0
    resistance_level: float = 0.0

def detect_regime(df: pd.DataFrame, config: ScalpConfig) -> RegimeInfo:
    """Piyasa rejimini tespit et"""
    info = RegimeInfo()
    
    if len(df) < config.regime_lookback_periods:
        return info
    
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    
    lookback = config.regime_lookback_periods
    recent_closes = closes[-lookback:]
    
    # Son değişim yüzdesi
    if recent_closes[0] > 0:
        info.recent_change_pct = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
    
    # Trend gücü (basit lineer regresyon eğimi)
    x = np.arange(lookback)
    slope = np.polyfit(x, recent_closes, 1)[0]
    info.trend_strength = abs(slope) / np.mean(recent_closes) * 100
    
    # Oversold/Overbought
    ind = TechnicalIndicators()
    rsi = ind.calc_rsi(closes, 14)
    current_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50.0
    
    info.is_oversold = current_rsi < config.regime_oversold_rsi
    info.is_overbought = current_rsi > 70.0
    
    # Support/Resistance (son N barda min/max)
    info.support_level = float(np.min(lows[-lookback:]))
    info.resistance_level = float(np.max(highs[-lookback:]))
    
    # Rejim belirleme
    if info.trend_strength > config.regime_trend_strength_threshold:
        if info.recent_change_pct > 0:
            info.regime = "TRENDING_UP"
        else:
            info.regime = "TRENDING_DOWN"
    else:
        info.regime = "RANGING"
    
    # Büyük düşüş modu (%4+ düşüş)
    if info.recent_change_pct < -config.regime_drop_threshold_pct:
        info.regime = "BIG_DROP"
    
    # Yüksek volatilite
    atr = ind.calc_atr(highs, lows, closes, 7)
    atr_pct = atr[-1] / closes[-1] * 100 if not np.isnan(atr[-1]) else 0.0
    if atr_pct > 1.5:
        info.regime = "VOLATILE"
    
    return info

def is_dip_buy_signal(closes: np.ndarray, regime: RegimeInfo, config: ScalpConfig) -> bool:
    """Dip alma sinyali kontrolü - büyük düşüş sonrası oversold"""
    if not config.regime_detection_enabled:
        return False
    
    # Büyük düşüş modunda ve oversold ise
    if regime.regime == "BIG_DROP" and regime.is_oversold:
        return True
    
    # %4+ düşüş ve RSI < 30
    if regime.recent_change_pct < -config.regime_drop_threshold_pct:
        ind = TechnicalIndicators()
        rsi = ind.calc_rsi(closes, 14)
        if not np.isnan(rsi[-1]) and rsi[-1] < config.regime_oversold_rsi:
            return True
    
    return False

def apply_regime_adjustments(scores: Dict[str, float], regime: RegimeInfo) -> Dict[str, float]:
    """Rejime göre skor ayarlamaları"""
    adjusted = scores.copy()
    
    if regime.regime == "TRENDING_UP":
        adjusted["ema_crossover"] *= 1.2
        adjusted["momentum_trigger"] *= 1.1
    
    elif regime.regime == "TRENDING_DOWN":
        adjusted["ema_crossover"] *= 0.8
        adjusted["momentum_trigger"] *= 0.7
    
    elif regime.regime == "BIG_DROP":
        adjusted["rsi_confirm"] *= 1.3
        adjusted["candle_pattern"] *= 1.2
    
    elif regime.regime == "VOLATILE":
        adjusted["atr_volatility"] *= 1.2
        adjusted["volume_spike"] *= 1.1
    
    elif regime.regime == "RANGING":
        adjusted["rsi_confirm"] *= 1.1
        adjusted["candle_pattern"] *= 1.1
    
    return adjusted

def calculate_confidence(scores: Dict[str, float]) -> Tuple[float, str]:
    """Ağırlıklı güven skoru hesaplama"""
    total = sum(scores.values())
    # Mevcut ağırlıkların toplamını hesapla (sabit yerine dinamik)
    max_score = sum(max(v, 1) for v in scores.values()) if scores else 100
    confidence = (total / max_score) * 100 if max_score > 0 else 0.0
    
    if confidence >= 85:
        level = "ÇOK YÜKSEK"
    elif confidence >= 72:
        level = "YÜKSEK"
    elif confidence >= 55:
        level = "ORTA"
    else:
        level = "DÜŞÜK"
    
    return round(confidence, 1), level


def evaluate_signal(df: pd.DataFrame, config: ScalpConfig, symbol: str = "") -> SignalResult:
    """Ana sinyal değerlendirme fonksiyonu"""
    result = SignalResult(signal="NONE", symbol=symbol)
    
    if len(df) < config.min_data_length:
        return result

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values
    opens = df["open"].values

    # ==================== REGIME DETECTION (ADX Bazlı) ====================
    if config.regime_filter_enabled:
        regime_detector = RegimeDetector(
            adx_period=config.regime_adx_period,
            atr_period=config.atr_period
        )
        regime_state = regime_detector.detect(
            highs, lows, closes,
            adx_threshold=config.regime_adx_threshold,
            atr_ratio_threshold=config.regime_atr_ratio_threshold
        )
        
        result.adx = regime_state.adx
        result.atr_ratio = regime_state.atr_ratio
        result.regime_state = regime_state.regime
        result.is_tradeable = regime_state.is_tradeable
        
        # Trade edilebilirlik kontrolü
        if not regime_state.is_tradeable:
            # Sert düşüş/yükseliş varsa yine de izin ver
            recent_change = (closes[-1] - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0
            if abs(recent_change) < 2.0:  # %2'den az değişim varsa engelle
                return result
        
        # ADX threshold kontrolü - gevşek
        if regime_state.adx < 15 and regime_state.adx > 0:  # Çok düşük ADX (ama hesaplanmışsa)
            return result
    
    # Eski regime detection (uyumluluk için)
    regime = detect_regime(df, config) if config.regime_detection_enabled else RegimeInfo()
    result.regime = regime.regime

    # ==================== İNDİKATÖRLER ====================
    ind = TechnicalIndicators()
    
    ema_fast = ind.calc_ema(closes, config.ema_fast)
    ema_slow = ind.calc_ema(closes, config.ema_slow)
    rsi = ind.calc_rsi(closes, config.rsi_period)
    atr = ind.calc_atr(highs, lows, closes, config.atr_period)
    macd, macd_signal, macd_hist = ind.calc_macd(closes)
    
    is_vol_spike, vol_ratio = ind.calc_volume_spike(
        volumes, 
        config.volume_lookback, 
        config.volume_spike_lookback, 
        config.volume_spike_mult
    )

    # ==================== TREND FİLTRESİ (200 EMA) ====================
    if config.trend_filter_enabled:
        ema_200 = ind.calc_ema(closes, config.trend_filter_ema_period)
        current_ema_200 = float(ema_200[-1]) if not np.isnan(ema_200[-1]) else None
    else:
        current_ema_200 = None

    # ==================== VOLUME CONDITION (Son 5 mumun 1.8x'i) ====================
    if config.volume_condition_enabled and len(volumes) >= config.volume_condition_lookback:
        recent_vol_avg = np.mean(volumes[-config.volume_condition_lookback:])
        base_vol_avg = np.mean(volumes[-(config.volume_condition_lookback * 3):-config.volume_condition_lookback])
        volume_condition_met = recent_vol_avg > base_vol_avg * config.volume_condition_mult if base_vol_avg > 0 else False
    else:
        volume_condition_met = True  # Varsayılan olarak geçir

    current_price = float(closes[-1])
    prev_price = float(closes[-2])

    # ==================== ORDER BOOK ANALİZİ ====================
    try:
        orderbook = get_order_book_analysis(symbol, current_price) if symbol else None
    except Exception:
        orderbook = None

    # ==================== DIP BUY CHECK ====================
    is_dip = is_dip_buy_signal(closes, regime, config)
    result.is_dip_buy = is_dip

    # ==================== PATTERN ANALİZ ====================
    pattern_analysis = full_candle_analysis(opens, highs, lows, closes, volumes)
    has_bullish_pattern = any(p in ["BULLISH_ENGULFING", "HAMMER", "STRONG_BULLISH"] 
                            for p in pattern_analysis["patterns"])
    has_bearish_pattern = any(p in ["BEARISH_ENGULFING", "SHOOTING_STAR", "STRONG_BEARISH"] 
                            for p in pattern_analysis["patterns"])

    # ==================== KOŞULLAR ====================
    # EMA Cross Strength hesapla
    ema_diff_pct = abs(ema_fast[-1] - ema_slow[-1]) / ema_slow[-1] * 100 if ema_slow[-1] > 0 else 0
    ema_cross_strength = ema_diff_pct * 10
    
    # ATR Ratio hesapla
    atr_ratio = atr[-1] / np.mean(atr[-20:]) if np.mean(atr[-20:]) > 0 else 1.0
    
    # Momentum hesapla
    momentum = (current_price - closes[-config.momentum_period]) / closes[-config.momentum_period] * 100 if len(closes) > config.momentum_period else 0
    
    # RSI momentum (yükseliyor mu?)
    rsi_momentum_positive = rsi[-1] > rsi[-3] if len(rsi) > 3 and not np.isnan(rsi[-1]) and not np.isnan(rsi[-3]) else False
    rsi_momentum_negative = rsi[-1] < rsi[-3] if len(rsi) > 3 and not np.isnan(rsi[-1]) and not np.isnan(rsi[-3]) else False
    
    # Candle ratio hesapla
    recent_candles = opens[-config.candle_period:]
    recent_closes_arr = closes[-config.candle_period:]
    bearish_count = sum(1 for o, c in zip(recent_candles, recent_closes_arr) if c < o)
    bullish_count = sum(1 for o, c in zip(recent_candles, recent_closes_arr) if c > o)
    bearish_ratio = bearish_count / config.candle_period
    bullish_ratio = bullish_count / config.candle_period
    
    # ===== LONG KOŞULLARI (Yeni config değerleri ile) =====
    long_ema = ind.check_crossover(ema_fast, ema_slow, "bullish") and ema_cross_strength >= config.long_ema_cross_threshold
    long_rsi = config.long_rsi_min <= rsi[-1] <= config.long_rsi_max and rsi_momentum_positive if not np.isnan(rsi[-1]) else False
    long_vol = is_vol_spike and vol_ratio >= config.long_volume_mult
    long_momentum = momentum >= config.long_momentum_min
    long_pattern = has_bullish_pattern and bullish_ratio >= config.long_candle_bullish_ratio
    long_atr = atr_ratio >= config.long_atr_ratio_min
    
    # Trend filtresi
    if config.trend_filter_enabled and current_ema_200 is not None:
        long_ema = long_ema and (current_price > current_ema_200)
    
    # Dip buy modunda RSI gevşet
    if is_dip and not long_rsi:
        long_rsi = rsi[-1] < 40 if not np.isnan(rsi[-1]) else False

    # ===== SHORT KOŞULLARI (Dengeli) =====
    # EMA bearish trend
    short_ema = ema_fast[-1] < ema_slow[-1]
    
    # Trend filtresi - 200 EMA altında olmalı
    if current_ema_200 and current_price > current_ema_200:
        short_ema = False
    
    # RSI - düşüş trendinde
    short_rsi = False
    if not np.isnan(rsi[-1]):
        if rsi[-1] < config.short_rsi_max:  # 50'in altında
            short_rsi = True
        elif rsi[-1] > 60 and rsi_momentum_negative:
            short_rsi = True
    
    # Volume
    short_vol = vol_ratio >= 1.5
    
    # Momentum - negatif olmalı
    short_momentum = momentum <= config.short_momentum_max
    
    # Pattern
    short_pattern = bearish_ratio >= config.short_candle_bearish_ratio
    
    # ATR
    short_atr = atr_ratio >= 1.0
    
    # Ek: Son 3 mumda düşüş trendi
    if len(closes) >= 3:
        last_3 = closes[-3:]
        if not (last_3[2] < last_3[1] < last_3[0]):
            short_momentum = False

    # ===== SKOR HESAPLAMA (Yeni skor sistemi) =====
    # SHORT skorları
    short_score = 0
    if short_ema: short_score += config.short_score_ema
    if short_rsi: short_score += config.short_score_rsi
    if short_vol: short_score += config.short_score_volume
    if short_atr: short_score += config.short_score_atr
    if short_momentum: short_score += config.short_score_momentum
    if short_pattern: short_score += config.short_score_candle
    
    # LONG skorları
    long_score = 0
    if long_ema: long_score += config.long_score_ema
    if long_rsi: long_score += config.long_score_rsi
    if long_vol: long_score += config.long_score_volume
    if long_atr: long_score += config.long_score_atr
    if long_momentum: long_score += config.long_score_momentum
    if long_pattern: long_score += config.long_score_candle
    
    # Ek bonuslar (LONG)
    if long_ema and current_ema_200 and current_price > current_ema_200:
        long_score += config.bonus_higher_low
    if orderbook and orderbook.is_tradeable and orderbook.imbalance > 0.2:
        long_score += config.bonus_orderbook
    
    # Ek bonuslar (SHORT)
    if short_ema and current_ema_200 and current_price < current_ema_200:
        short_score += config.bonus_lower_high
    if orderbook and orderbook.is_tradeable and orderbook.imbalance < -0.2:
        short_score += config.bonus_orderbook
    
    # Eski skor sistemi (uyumluluk için)
    long_scores = {
        "ema_crossover": config.long_score_ema if long_ema else 0,
        "rsi_confirm": config.long_score_rsi if long_rsi else 0,
        "volume_spike": config.long_score_volume if long_vol else 0,
        "atr_volatility": config.long_score_atr if long_atr else 0,
        "momentum_trigger": config.long_score_momentum if long_momentum else 0,
        "candle_pattern": config.long_score_candle if long_pattern else 0,
    }

    short_scores = {
        "ema_crossover": config.short_score_ema if short_ema else 0,
        "rsi_confirm": config.short_score_rsi if short_rsi else 0,
        "volume_spike": config.short_score_volume if short_vol else 0,
        "atr_volatility": config.short_score_atr if short_atr else 0,
        "momentum_trigger": config.short_score_momentum if short_momentum else 0,
        "candle_pattern": config.short_score_candle if short_pattern else 0,
    }

    # Rejime göre skor ayarla
    if config.regime_detection_enabled:
        long_scores = apply_regime_adjustments(long_scores, regime)
        short_scores = apply_regime_adjustments(short_scores, regime)

    # Dip buy modunda Long skorunu artır
    if is_dip:
        long_score += 15

    long_conf, long_level = calculate_confidence(long_scores)
    short_conf, short_level = calculate_confidence(short_scores)

    # ==================== SİNYAL KARARI ====================
    # Minimum koşul kontrolü
    long_met_conditions = sum([long_ema, long_rsi, long_vol, long_atr, long_momentum, long_pattern])
    short_met_conditions = sum([short_ema, short_rsi, short_vol, short_atr, short_momentum, short_pattern])
    
    if long_met_conditions < config.min_conditions and short_met_conditions < config.min_conditions:
        result.met_conditions = max(long_met_conditions, short_met_conditions)
        return result
    
    result.met_conditions = max(long_met_conditions, short_met_conditions)
    result.score = max(long_score, short_score)

    # Doğrudan short sinyali ver (basitleştirilmiş)
    atr_val = float(atr[-1]) if not np.isnan(atr[-1]) else current_price * 0.01
    
    if config.dynamic_sl_enabled:
        sl_distance = atr_val * config.sl_atr_multiplier
        sl_price = current_price + sl_distance
        tp1_price = current_price - sl_distance * 1.0
        tp2_price = current_price - sl_distance * 2.0
        tp3_price = current_price - sl_distance * 3.0
    else:
        sl_distance = current_price * (config.short_sl_pct_min / 100 + config.short_sl_pct_max / 100) / 2
        sl_price = current_price + sl_distance
        tp1_price = current_price * (1 - config.short_tp1_pct / 100)
        tp2_price = current_price * (1 - config.short_tp2_pct / 100)
        tp3_price = current_price * (1 - config.short_tp3_pct / 100)
    
    leverage = max(config.short_leverage_min, min(config.short_leverage_max, config.leverage))
    
    risk = sl_price - current_price
    reward = current_price - tp3_price
    risk_reward = reward / risk if risk > 0 else 0
    
    # SHORT sinyali
    if short_met_conditions >= config.min_conditions and risk_reward >= config.min_risk_reward:
        result.signal = "SHORT"
        result.entry_price = current_price
        result.sl_price = sl_price
        result.tp1_price = tp1_price
        result.tp2_price = tp2_price
        result.tp3_price = tp3_price
        result.leverage = leverage
        result.confidence = 85.0
        result.confidence_level = "YÜKSEK"
        result.score = short_score if short_score > 0 else 75
        result.met_conditions = short_met_conditions
        result.conditions = {k: v > 0 for k, v in short_scores.items()}
        result.condition_scores = short_scores
        result.patterns = pattern_analysis["patterns"]
        result.risk_reward = round(risk_reward, 2)
        
        return result
    
    # LONG sinyali
    if long_met_conditions >= config.min_conditions:
        if config.dynamic_sl_enabled:
            sl_distance = atr_val * config.sl_atr_multiplier
            sl_price = current_price - sl_distance
            tp1_price = current_price + sl_distance * 1.0
            tp2_price = current_price + sl_distance * 2.0
            tp3_price = current_price + sl_distance * 3.0
        else:
            sl_distance = current_price * (config.long_sl_pct_min / 100 + config.long_sl_pct_max / 100) / 2
            sl_price = current_price - sl_distance
            tp1_price = current_price * (1 + config.long_tp1_pct / 100)
            tp2_price = current_price * (1 + config.long_tp2_pct / 100)
            tp3_price = current_price * (1 + config.long_tp3_pct / 100)
        
        leverage = max(config.long_leverage_min, min(config.long_leverage_max, config.leverage))
        risk = current_price - sl_price
        reward = tp3_price - current_price
        risk_reward = reward / risk if risk > 0 else 0
        
        if risk_reward >= config.min_risk_reward:
            result.signal = "LONG"
            result.entry_price = current_price
            result.sl_price = sl_price
            result.tp1_price = tp1_price
            result.tp2_price = tp2_price
            result.tp3_price = tp3_price
            result.leverage = leverage
            result.confidence = 85.0
            result.confidence_level = "YÜKSEK"
            result.score = long_score if long_score > 0 else 75
            result.met_conditions = long_met_conditions
            result.conditions = {k: v > 0 for k, v in long_scores.items()}
            result.condition_scores = long_scores
            result.patterns = pattern_analysis["patterns"]
            result.risk_reward = round(risk_reward, 2)

    return result
