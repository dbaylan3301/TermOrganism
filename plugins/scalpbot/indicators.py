import numpy as np
from typing import Tuple, Dict, Optional

class TechnicalIndicators:
    """Teknik indikatörler kütüphanesi - Trading botu için optimize edildi."""

    @staticmethod
    def calc_ema(prices: np.ndarray, period: int = 12) -> np.ndarray:
        """Exponential Moving Average"""
        if len(prices) < period or period < 1:
            return np.full_like(prices, np.nan, dtype=float)
        
        ema = np.full_like(prices, np.nan, dtype=float)
        valid = prices[:period][~np.isnan(prices[:period])]
        if len(valid) == 0:
            return ema
        ema[period-1] = np.mean(valid)
        
        multiplier = 2.0 / (period + 1)
        for i in range(period, len(prices)):
            ema[i] = prices[i] * multiplier + ema[i-1] * (1 - multiplier)
        return ema

    @staticmethod
    def calc_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index (Wilder's method)"""
        if len(prices) < period + 1:
            return np.full_like(prices, np.nan, dtype=float)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        rsi = np.full_like(prices, np.nan, dtype=float)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - (100.0 / (1.0 + rs))
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi

    @staticmethod
    def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                 period: int = 14) -> np.ndarray:
        """Average True Range - Wilder's method"""
        n = len(highs)
        if n < period + 1 or len(lows) != n or len(closes) != n:
            return np.full_like(highs, np.nan, dtype=float)
        
        tr = np.maximum.reduce([
            highs[1:] - lows[1:],
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        ])
        
        atr = np.full(n, np.nan, dtype=float)
        atr[period] = np.mean(tr[:period])
        
        for i in range(period, len(tr)):
            atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
        
        return atr

    @staticmethod
    def calc_macd(prices: np.ndarray, fast: int = 12, slow: int = 26,
                  signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD, Signal ve Histogram"""
        ema_fast = TechnicalIndicators.calc_ema(prices, fast)
        ema_slow = TechnicalIndicators.calc_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.calc_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calc_bollinger_bands(prices: np.ndarray, period: int = 20, std_mult: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands"""
        if len(prices) < period:
            return (np.full_like(prices, np.nan), 
                    np.full_like(prices, np.nan), 
                    np.full_like(prices, np.nan))
        
        sma = np.full_like(prices, np.nan)
        upper = np.full_like(prices, np.nan)
        lower = np.full_like(prices, np.nan)
        
        for i in range(period-1, len(prices)):
            window = prices[i-period+1:i+1]
            sma[i] = np.mean(window)
            std = np.std(window, ddof=0)
            upper[i] = sma[i] + std_mult * std
            lower[i] = sma[i] - std_mult * std
        
        return upper, sma, lower

    @staticmethod
    def calc_supertrend(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                       period: int = 10, multiplier: float = 3.0) -> Tuple[np.ndarray, np.ndarray]:
        """Supertrend Indicator"""
        n = len(highs)
        if n < period:
            return np.full(n, np.nan), np.full(n, np.nan)
        
        atr = TechnicalIndicators.calc_atr(highs, lows, closes, period)
        upper_band = (highs + lows) / 2 + multiplier * atr
        lower_band = (highs + lows) / 2 - multiplier * atr
        
        supertrend = np.full(n, np.nan)
        direction = np.full(n, 1)  # 1 = uptrend, -1 = downtrend
        
        for i in range(period, n):
            if np.isnan(atr[i]):
                continue
                
            if closes[i-1] > upper_band[i-1]:
                direction[i] = 1
            elif closes[i-1] < lower_band[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
                
            if direction[i] == 1:
                supertrend[i] = lower_band[i]
            else:
                supertrend[i] = upper_band[i]
        
        return supertrend, direction

    @staticmethod
    def calc_stochastic_rsi(prices: np.ndarray, rsi_period: int = 14,
                           stoch_period: int = 14) -> np.ndarray:
        """Stochastic RSI"""
        rsi = TechnicalIndicators.calc_rsi(prices, rsi_period)
        if len(rsi) < stoch_period:
            return np.full_like(prices, np.nan)
        
        stoch_rsi = np.full_like(prices, np.nan)
        for i in range(stoch_period + rsi_period, len(rsi)):
            window = rsi[i-stoch_period:i]
            if np.all(np.isnan(window)):
                continue
            min_rsi = np.nanmin(window)
            max_rsi = np.nanmax(window)
            if max_rsi - min_rsi == 0:
                stoch_rsi[i] = 50.0
            else:
                stoch_rsi[i] = (rsi[i] - min_rsi) / (max_rsi - min_rsi) * 100
        return stoch_rsi

    @staticmethod
    def calc_volume_spike(volumes: np.ndarray, lookback: int = 20,
                         spike_lookback: int = 5, mult: float = 1.8) -> Tuple[bool, float]:
        """Volume Spike Detection"""
        if len(volumes) < lookback + spike_lookback:
            return False, 0.0
        
        valid_vol = volumes[volumes > 0]
        if len(valid_vol) < lookback + spike_lookback:
            return False, 0.0
        
        recent_avg = np.mean(valid_vol[-spike_lookback:])
        base_avg = np.mean(valid_vol[-(lookback + spike_lookback):-spike_lookback])
        
        if base_avg <= 0:
            return False, 0.0
        
        ratio = recent_avg / base_avg
        return ratio >= mult, ratio

    @staticmethod
    def check_crossover(fast: np.ndarray, slow: np.ndarray, direction: str = "bullish") -> bool:
        """EMA/MACD vs. için crossover kontrolü"""
        if len(fast) < 2 or len(slow) < 2:
            return False
        if any(np.isnan(x) for x in [fast[-1], slow[-1], fast[-2], slow[-2]]):
            return False
        
        if direction == "bullish":
            return fast[-2] <= slow[-2] and fast[-1] > slow[-1]
        elif direction == "bearish":
            return fast[-2] >= slow[-2] and fast[-1] < slow[-1]
        return False

    @staticmethod
    def get_all_indicators(ohlcv: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Tüm indikatörleri tek seferde hesapla (performans için)"""
        closes = ohlcv['close']
        highs = ohlcv.get('high', closes)
        lows = ohlcv.get('low', closes)
        volumes = ohlcv.get('volume', np.zeros_like(closes))
        
        indicators = {
            'ema_fast': TechnicalIndicators.calc_ema(closes, 9),
            'ema_slow': TechnicalIndicators.calc_ema(closes, 21),
            'rsi': TechnicalIndicators.calc_rsi(closes, 14),
            'macd': TechnicalIndicators.calc_macd(closes)[0],
            'macd_signal': TechnicalIndicators.calc_macd(closes)[1],
            'macd_hist': TechnicalIndicators.calc_macd(closes)[2],
            'bb_upper': TechnicalIndicators.calc_bollinger_bands(closes)[0],
            'bb_middle': TechnicalIndicators.calc_bollinger_bands(closes)[1],
            'bb_lower': TechnicalIndicators.calc_bollinger_bands(closes)[2],
            'atr': TechnicalIndicators.calc_atr(highs, lows, closes, 14),
            'supertrend': TechnicalIndicators.calc_supertrend(highs, lows, closes)[0],
        }
        return indicators
