# plugins/scalpbot/ai/symbolic/fuzzy_logic.py
"""Fuzzy logic for trading decisions."""

import numpy as np
from typing import Dict, Tuple


class FuzzyMembership:
    """Fuzzy membership functions."""
    
    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """Triangular membership function."""
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:
            return (c - x) / (c - b)
    
    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """Trapezoidal membership function."""
        if x <= a or x >= d:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        elif b < x <= c:
            return 1.0
        else:
            return (d - x) / (d - c)
    
    @staticmethod
    def gaussian(x: float, mean: float, sigma: float) -> float:
        """Gaussian membership function."""
        return np.exp(-0.5 * ((x - mean) / sigma) ** 2)


class FuzzyTradingSystem:
    """
    Fuzzy logic system for trading.
    Converts crisp values to fuzzy sets and applies rules.
    """
    
    def __init__(self):
        self.mf = FuzzyMembership()
    
    def fuzzify_rsi(self, rsi: float) -> Dict[str, float]:
        """Fuzzify RSI value."""
        return {
            "oversold": self.mf.trapezoidal(rsi, 0, 0, 25, 35),
            "neutral": self.mf.triangular(rsi, 25, 50, 75),
            "overbought": self.mf.trapezoidal(rsi, 65, 75, 100, 100)
        }
    
    def fuzzify_volume(self, volume_ratio: float) -> Dict[str, float]:
        """Fuzzify volume ratio."""
        return {
            "low": self.mf.trapezoidal(volume_ratio, 0, 0, 0.5, 1.0),
            "normal": self.mf.triangular(volume_ratio, 0.5, 1.0, 2.0),
            "high": self.mf.trapezoidal(volume_ratio, 1.5, 2.0, 5.0, 5.0)
        }
    
    def fuzzify_momentum(self, momentum: float) -> Dict[str, float]:
        """Fuzzify momentum value."""
        return {
            "negative": self.mf.trapezoidal(momentum, -1, -1, -0.3, 0),
            "neutral": self.mf.triangular(momentum, -0.3, 0, 0.3),
            "positive": self.mf.trapezoidal(momentum, 0, 0.3, 1, 1)
        }
    
    def apply_rules(self, rsi_fuzzy: Dict, volume_fuzzy: Dict, 
                    momentum_fuzzy: Dict) -> Dict[str, float]:
        """Apply fuzzy rules."""
        rules = {
            "strong_buy": min(rsi_fuzzy["oversold"], volume_fuzzy["high"], momentum_fuzzy["positive"]),
            "buy": min(rsi_fuzzy["oversold"], volume_fuzzy["normal"]),
            "hold": max(rsi_fuzzy["neutral"], min(volume_fuzzy["normal"], momentum_fuzzy["neutral"])),
            "sell": min(rsi_fuzzy["overbought"], volume_fuzzy["normal"]),
            "strong_sell": min(rsi_fuzzy["overbought"], volume_fuzzy["high"], momentum_fuzzy["negative"])
        }
        return rules
    
    def defuzzify(self, rules: Dict[str, float]) -> Tuple[str, float]:
        """Defuzzify to crisp decision."""
        # Weighted average defuzzification
        action_weights = {
            "strong_buy": 2.0,
            "buy": 1.0,
            "hold": 0.0,
            "sell": -1.0,
            "strong_sell": -2.0
        }
        
        weighted_sum = sum(rules[a] * action_weights[a] for a in rules)
        weight_sum = sum(rules.values())
        
        if weight_sum == 0:
            return "hold", 0.5
        
        crisp_value = weighted_sum / weight_sum
        
        if crisp_value > 0.5:
            return "strong_buy", min(0.9, 0.5 + crisp_value * 0.2)
        elif crisp_value > 0.1:
            return "buy", 0.6 + crisp_value * 0.1
        elif crisp_value < -0.5:
            return "strong_sell", min(0.9, 0.5 + abs(crisp_value) * 0.2)
        elif crisp_value < -0.1:
            return "sell", 0.6 + abs(crisp_value) * 0.1
        else:
            return "hold", 0.5
    
    def evaluate(self, rsi: float, volume_ratio: float, 
                momentum: float) -> Tuple[str, float]:
        """Full fuzzy evaluation."""
        rsi_fuzzy = self.fuzzify_rsi(rsi)
        volume_fuzzy = self.fuzzify_volume(volume_ratio)
        momentum_fuzzy = self.fuzzify_momentum(momentum)
        
        rules = self.apply_rules(rsi_fuzzy, volume_fuzzy, momentum_fuzzy)
        return self.defuzzify(rules)
