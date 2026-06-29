"""Regime Detection ve Volatilite Filter - ADX bazlı."""

import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class RegimeState:
    regime: str = "UNKNOWN"  # TRENDING, RANGING, VOLATILE
    adx: float = 0.0
    atr_ratio: float = 1.0
    is_tradeable: bool = True
    confidence: float = 0.0
    reason: str = ""

class RegimeDetector:
    """ADX bazlı piyasa rejimi tespiti."""
    
    def __init__(self, adx_period: int = 14, atr_period: int = 14):
        self.adx_period = adx_period
        self.atr_period = atr_period
    
    def calc_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
        """ADX hesapla (Wilder's method)."""
        n = len(highs)
        if n < self.adx_period * 2:
            return np.full(n, np.nan)
        
        # True Range
        tr = np.maximum.reduce([
            highs[1:] - lows[1:],
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        ])
        
        # Directional Movement
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Wilder's smoothing
        atr_smooth = np.full(n, np.nan)
        plus_dm_smooth = np.full(n, np.nan)
        minus_dm_smooth = np.full(n, np.nan)
        
        atr_smooth[self.adx_period] = np.sum(tr[:self.adx_period])
        plus_dm_smooth[self.adx_period] = np.sum(plus_dm[:self.adx_period])
        minus_dm_smooth[self.adx_period] = np.sum(minus_dm[:self.adx_period])
        
        for i in range(self.adx_period, n - 1):
            atr_smooth[i + 1] = atr_smooth[i] - atr_smooth[i] / self.adx_period + tr[i]
            plus_dm_smooth[i + 1] = plus_dm_smooth[i] - plus_dm_smooth[i] / self.adx_period + plus_dm[i]
            minus_dm_smooth[i + 1] = minus_dm_smooth[i] - minus_dm_smooth[i] / self.adx_period + minus_dm[i]
        
        # DI+ ve DI- (güvenli bölme)
        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = np.where(atr_smooth > 0, 100 * plus_dm_smooth / atr_smooth, 0.0)
            minus_di = np.where(atr_smooth > 0, 100 * minus_dm_smooth / atr_smooth, 0.0)
            plus_di = np.nan_to_num(plus_di, nan=0.0)
            minus_di = np.nan_to_num(minus_di, nan=0.0)
        
        # DX (güvenli bölme)
        with np.errstate(divide='ignore', invalid='ignore'):
            di_sum = plus_di + minus_di
            dx = np.where(di_sum > 0, 100 * np.abs(plus_di - minus_di) / di_sum, 0.0)
            dx = np.nan_to_num(dx, nan=0.0)
        
        # ADX (Wilder's smoothing)
        adx = np.full(n, np.nan)
        adx[self.adx_period * 2] = np.nanmean(dx[self.adx_period:self.adx_period * 2])
        
        for i in range(self.adx_period * 2, n - 1):
            if not np.isnan(adx[i]) and not np.isnan(dx[i]):
                adx[i + 1] = (adx[i] * (self.adx_period - 1) + dx[i]) / self.adx_period
        
        return adx
    
    def calc_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
        """ATR hesapla."""
        n = len(highs)
        if n < self.atr_period + 1:
            return np.full(n, np.nan)
        
        tr = np.maximum.reduce([
            highs[1:] - lows[1:],
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        ])
        
        atr = np.full(n, np.nan)
        atr[self.atr_period] = np.mean(tr[:self.atr_period])
        
        for i in range(self.atr_period, len(tr)):
            atr[i + 1] = (atr[i] * (self.atr_period - 1) + tr[i]) / self.atr_period
        
        return atr
    
    def detect(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
               adx_threshold: float = 25.0, atr_ratio_threshold: float = 1.4) -> RegimeState:
        """Piyasa rejimini tespit et."""
        state = RegimeState()
        
        if len(highs) < self.adx_period * 3:
            state.is_tradeable = False
            state.reason = "Yetersiz veri"
            return state
        
        # ADX hesapla
        adx = self.calc_adx(highs, lows, closes)
        current_adx = float(adx[-1]) if not np.isnan(adx[-1]) else 0
        state.adx = current_adx
        
        # ATR hesapla
        atr = self.calc_atr(highs, lows, closes)
        
        # ATR ratio (mevcut / ortalama)
        if len(atr) > 20:
            atr_20 = np.nanmean(atr[-20:])
            current_atr = atr[-1] if not np.isnan(atr[-1]) else 0
            state.atr_ratio = current_atr / atr_20 if atr_20 > 0 else 1.0
        
        # Rejim belirleme
        if current_adx >= adx_threshold:
            state.regime = "TRENDING"
            state.confidence = min(current_adx / 50, 1.0)
        else:
            state.regime = "RANGING"
            state.confidence = 1.0 - (current_adx / adx_threshold)
        
        # Yüksek volatilite kontrolü
        if state.atr_ratio > 2.0:
            state.regime = "VOLATILE"
            state.confidence = min(state.atr_ratio / 3.0, 1.0)
        
        # Trade edilebilirlik kontrolü
        if state.regime == "RANGING" and state.atr_ratio < atr_ratio_threshold:
            state.is_tradeable = False
            state.reason = f"Yan piyasa + düşük volatilite (ATR ratio: {state.atr_ratio:.2f})"
        elif state.regime == "VOLATILE" and state.atr_ratio > 3.0:
            state.is_tradeable = False
            state.reason = f"Aşırı volatilite (ATR ratio: {state.atr_ratio:.2f})"
        else:
            state.is_tradeable = True
            state.reason = f"{state.regime} - ADX:{current_adx:.1f} ATR ratio:{state.atr_ratio:.2f}"
        
        return state


def detect_regime_simple(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                        adx_threshold: float = 25.0) -> str:
    """Basit rejim tespidi (sadece TRENDING/RANGING)."""
    detector = RegimeDetector()
    state = detector.detect(highs, lows, closes, adx_threshold)
    return state.regime
