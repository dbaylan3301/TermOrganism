"""Meta-learner for ensemble fusion."""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from .voting import WeightedVoter


@dataclass
class MetaPrediction:
    """Meta-learner prediction."""
    direction: str
    confidence: float
    model_contributions: Dict[str, float]
    ensemble_method: str


class MetaLearner:
    """Meta-learner that combines all brain predictions."""
    
    def __init__(self):
        self.voter = WeightedVoter()
        self.model_performance = {}
        self.prediction_history = []
    
    def predict(self, predictions: Dict[str, Tuple[str, float]], 
                method: str = "weighted_voting") -> MetaPrediction:
        """
        Make ensemble prediction.
        predictions: {model_name: (direction, confidence)}
        """
        if method == "weighted_voting":
            direction, confidence = self.voter.vote(predictions)
        elif method == "confidence_threshold":
            direction, confidence = self._confidence_threshold(predictions)
        elif method == "majority_vote":
            direction, confidence = self._majority_vote(predictions)
        else:
            direction, confidence = self.voter.vote(predictions)
        
        # Calculate contributions
        contributions = {}
        for model_name, (dir_, conf) in predictions.items():
            weight = self.voter.weights.get(model_name, 0.1)
            contributions[model_name] = weight * conf
        
        return MetaPrediction(
            direction=direction,
            confidence=confidence,
            model_contributions=contributions,
            ensemble_method=method
        )
    
    def _confidence_threshold(self, predictions: Dict[str, Tuple[str, float]],
                             threshold: float = 0.7) -> Tuple[str, float]:
        """Only use predictions with high confidence."""
        high_conf_predictions = {
            k: v for k, v in predictions.items() 
            if v[1] >= threshold
        }
        
        if not high_conf_predictions:
            # Fall back to best prediction
            best = max(predictions.values(), key=lambda x: x[1])
            return best
        
        return self.voter.vote(high_conf_predictions)
    
    def _majority_vote(self, predictions: Dict[str, Tuple[str, float]]) -> Tuple[str, float]:
        """Simple majority voting."""
        votes = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}
        
        for direction, confidence in predictions.values():
            if direction in votes:
                votes[direction] += 1
        
        winner = max(votes, key=votes.get)
        confidence = votes[winner] / len(predictions) if predictions else 0
        
        return winner, confidence
    
    def update_performance(self, model_name: str, correct: bool):
        """Update model performance tracking."""
        if model_name not in self.model_performance:
            self.model_performance[model_name] = {"correct": 0, "total": 0}
        
        self.model_performance[model_name]["total"] += 1
        if correct:
            self.model_performance[model_name]["correct"] += 1
        
        # Update weights based on performance
        perf = self.model_performance[model_name]
        accuracy = perf["correct"] / perf["total"] if perf["total"] > 0 else 0.5
        self.voter.update_weights(model_name, accuracy)
