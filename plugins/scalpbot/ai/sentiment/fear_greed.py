"""Fear & Greed Index analyzer."""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class FearGreedData:
    """Fear & Greed Index data."""
    value: int  # 0-100
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: float


class FearGreedIndex:
    """Calculate Fear & Greed Index."""
    
    LABELS = {
        (0, 25): "Extreme Fear",
        (25, 45): "Fear",
        (45, 55): "Neutral",
        (55, 75): "Greed",
        (75, 100): "Extreme Greed"
    }
    
    def __init__(self):
        self.history = []
    
    def calculate_from_data(self, prices: np.ndarray, volumes: np.ndarray,
                           momentum_period: int = 20) -> FearGreedData:
        """Calculate Fear & Greed from market data."""
        # Price momentum
        if len(prices) > momentum_period:
            price_change = (prices[-1] - prices[-momentum_period]) / prices[-momentum_period]
            momentum_score = self._normalize(price_change, -0.3, 0.3)
        else:
            momentum_score = 50
        
        # Volume momentum
        if len(volumes) > momentum_period:
            vol_change = np.mean(volumes[-5:]) / np.mean(volumes[-momentum_period:-5])
            volume_score = self._normalize(vol_change, 0.5, 2.0)
        else:
            volume_score = 50
        
        # Volatility (inverse relationship)
        if len(prices) > 20:
            returns = np.diff(prices[-20:]) / prices[-20:-1]
            volatility = np.std(returns)
            volatility_score = 100 - self._normalize(volatility, 0.01, 0.1)
        else:
            volatility_score = 50
        
        # Combine scores
        value = int(momentum_score * 0.4 + volume_score * 0.3 + volatility_score * 0.3)
        value = max(0, min(100, value))
        
        # Get label
        label = "Neutral"
        for (low, high), lbl in self.LABELS.items():
            if low <= value < high:
                label = lbl
                break
        
        return FearGreedData(value=value, label=label, timestamp=time.time())
    
    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-100 range."""
        normalized = (value - min_val) / (max_val - min_val)
        return max(0, min(100, normalized * 100))
    
    def get_trading_signal(self, data: FearGreedData) -> str:
        """Get trading signal from Fear & Greed Index."""
        if data.value < 25:
            return "STRONG_BUY"  # Extreme Fear = buying opportunity
        elif data.value < 40:
            return "BUY"
        elif data.value > 75:
            return "STRONG_SELL"  # Extreme Greed = selling opportunity
        elif data.value > 60:
            return "SELL"
        else:
            return "NEUTRAL"