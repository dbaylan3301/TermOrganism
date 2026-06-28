"""Weighted voting ensemble."""

import numpy as np
from typing import Dict, List, Tuple


class WeightedVoter:
    """Weighted voting for ensemble predictions."""
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "lstm": 0.25,
            "transformer": 0.25,
            "q_learning": 0.20,
            "ppo": 0.20,
            "sentiment": 0.10
        }
    
    def vote(self, predictions: Dict[str, Tuple[str, float]]) -> Tuple[str, float]:
        """
        Weighted voting.
        predictions: {model_name: (direction, confidence)}
        """
        votes = {"LONG": 0.0, "SHORT": 0.0, "NEUTRAL": 0.0}
        
        for model_name, (direction, confidence) in predictions.items():
            weight = self.weights.get(model_name, 0.1)
            if direction in votes:
                votes[direction] += weight * confidence
        
        # Get winner
        winner = max(votes, key=votes.get)
        total = sum(votes.values())
        
        if total > 0:
            confidence = votes[winner] / total
        else:
            confidence = 0.0
        
        return winner, confidence
    
    def update_weights(self, model_name: str, performance: float):
        """Update model weight based on performance."""
        if model_name in self.weights:
            # Simple adaptive weighting
            self.weights[model_name] = performance
        
        # Normalize
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}
