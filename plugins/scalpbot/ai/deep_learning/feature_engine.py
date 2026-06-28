# plugins/scalpbot/ai/deep_learning/feature_engine.py
"""Feature extraction engine for AI models."""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Features:
    """Extracted features for AI models."""
    price_features: np.ndarray
    volume_features: np.ndarray
    technical_features: np.ndarray
    pattern_features: np.ndarray
    temporal_features: np.ndarray
    labels: np.ndarray = None


class FeatureEngine:
    """Extract and normalize features for AI models."""
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
    
    def extract_price_features(self, closes: np.ndarray) -> np.ndarray:
        """Extract price-based features."""
        features = []
        
        # Returns
        returns = np.diff(closes) / closes[:-1]
        features.append(returns[-self.lookback:])
        
        # Log returns
        log_returns = np.log(closes[1:] / closes[:-1])
        features.append(log_returns[-self.lookback:])
        
        # Price momentum
        momentum_5 = closes[-5:] / closes[-10:-5] - 1
        momentum_10 = closes[-10:] / closes[-20:-10] - 1
        features.append([momentum_5.mean(), momentum_10.mean()])
        
        # Volatility
        volatility = np.std(returns[-20:])
        features.append([volatility])
        
        return np.concatenate(features)
    
    def extract_volume_features(self, volumes: np.ndarray) -> np.ndarray:
        """Extract volume-based features."""
        features = []
        
        # Volume changes
        vol_changes = np.diff(volumes) / (volumes[:-1] + 1e-10)
        features.append(vol_changes[-self.lookback:])
        
        # Volume momentum
        recent_vol = volumes[-5:].mean()
        base_vol = volumes[-20:-5].mean()
        vol_momentum = recent_vol / (base_vol + 1e-10)
        features.append([vol_momentum])
        
        # Volume volatility
        vol_volatility = np.std(volumes[-20:])
        features.append([vol_volatility])
        
        return np.concatenate(features)
    
    def extract_technical_features(self, indicators: Dict[str, np.ndarray]) -> np.ndarray:
        """Extract technical indicator features."""
        features = []
        
        # RSI
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if isinstance(rsi, np.ndarray) and len(rsi) > 0:
                features.extend([rsi[-1], rsi[-5:].mean() if len(rsi) >= 5 else rsi[-1]])
            else:
                features.extend([float(rsi), float(rsi)])
        
        # MACD
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            if isinstance(macd, np.ndarray) and len(macd) > 0:
                features.extend([macd[-1], signal[-1], macd[-1] - signal[-1]])
            else:
                features.extend([float(macd), float(signal), float(macd) - float(signal)])
        
        # Bollinger Bands
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            upper = indicators['bb_upper']
            lower = indicators['bb_lower']
            if isinstance(upper, np.ndarray) and len(upper) > 0:
                bb_position = (upper[-1] - lower[-1]) / (upper[-1] + lower[-1] + 1e-10)
            else:
                bb_position = (float(upper) - float(lower)) / (float(upper) + float(lower) + 1e-10)
            features.append(bb_position)
        
        # ATR
        if 'atr' in indicators:
            atr = indicators['atr']
            if isinstance(atr, np.ndarray) and len(atr) > 0:
                features.append(atr[-1])
            else:
                features.append(float(atr))
        
        return np.array(features)
    
    def extract_pattern_features(self, patterns: List[str]) -> np.ndarray:
        """Extract candle pattern features."""
        pattern_list = [
            "BULLISH_ENGULFING", "BEARISH_ENGULFING",
            "HAMMER", "SHOOTING_STAR",
            "STRONG_BULLISH", "STRONG_BEARISH",
            "DOJI", "MORNING_STAR", "EVENING_STAR"
        ]
        
        features = [1.0 if p in patterns else 0.0 for p in pattern_list]
        return np.array(features)
    
    def extract_temporal_features(self, timestamp) -> np.ndarray:
        """Extract time-based features."""
        import datetime
        if hasattr(timestamp, 'to_pydatetime'):
            dt = timestamp.to_pydatetime()
        elif isinstance(timestamp, (int, float)):
            dt = datetime.datetime.fromtimestamp(timestamp)
        else:
            dt = datetime.datetime.now()
        
        features = [
            dt.hour / 24.0,  # Hour of day
            dt.weekday() / 7.0,  # Day of week
            dt.minute / 60.0,  # Minute of hour
        ]
        
        # Session flags (UTC)
        features.append(1.0 if 13 <= dt.hour <= 21 else 0.0)  # US session
        features.append(1.0 if 7 <= dt.hour <= 16 else 0.0)  # EU session
        features.append(1.0 if 0 <= dt.hour <= 9 else 0.0)  # Asia session
        
        return np.array(features)
    
    def extract_all(self, df, indicators: Dict[str, np.ndarray], 
                    patterns: List[str]) -> Features:
        """Extract all features."""
        closes = df['close'].values
        volumes = df['volume'].values
        
        price_features = self.extract_price_features(closes)
        volume_features = self.extract_volume_features(volumes)
        technical_features = self.extract_technical_features(indicators)
        pattern_features = self.extract_pattern_features(patterns)
        temporal_features = self.extract_temporal_features(df.index[-1])
        
        return Features(
            price_features=price_features,
            volume_features=volume_features,
            technical_features=technical_features,
            pattern_features=pattern_features,
            temporal_features=temporal_features
        )