# plugins/scalpbot/ai/deep_learning/transformer_model.py
"""Transformer-based price predictor."""

import numpy as np
from typing import Optional
from dataclasses import dataclass
from .attention import TransformerBlock


@dataclass
class TransformerPrediction:
    """Transformer prediction result."""
    direction: str
    confidence: float
    attention_weights: np.ndarray
    predicted_return: float


class TransformerPredictor:
    """Transformer model for price prediction."""

    def __init__(self, d_model: int = 64, num_heads: int = 4,
                 num_layers: int = 3, d_ff: int = 128,
                 max_seq_len: int = 100):
        self.d_model = d_model
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.d_ff = d_ff
        self.max_seq_len = max_seq_len

        self.pos_encoding = self._create_positional_encoding()

        self.blocks = [
            TransformerBlock(d_model, num_heads, d_ff)
            for _ in range(num_layers)
        ]

        self.output_proj = np.random.randn(d_model, 3) * 0.01

    def _create_positional_encoding(self) -> np.ndarray:
        pe = np.zeros((self.max_seq_len, self.d_model))
        position = np.arange(0, self.max_seq_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, self.d_model, 2) *
                         -(np.log(10000.0) / self.d_model))

        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)

        return pe

    def project_to_d_model(self, features: np.ndarray) -> np.ndarray:
        if features.shape[-1] == self.d_model:
            return features

        projection = np.random.randn(features.shape[-1], self.d_model) * 0.01
        return np.dot(features, projection)

    def softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

    def forward(self, features: np.ndarray,
                mask: Optional[np.ndarray] = None) -> TransformerPrediction:
        if len(features.shape) == 2:
            features = features[np.newaxis, :]

        x = self.project_to_d_model(features)

        seq_len = min(x.shape[1], self.max_seq_len)
        x = x[:, :seq_len, :] + self.pos_encoding[:seq_len, :]

        attention_weights = []
        for block in self.blocks:
            x = block.forward(x, mask)
            attention_weights.append(np.ones((x.shape[1], x.shape[1])) / x.shape[1])

        x = np.mean(x, axis=1)

        logits = np.dot(x, self.output_proj)
        probs = self.softmax(logits, axis=-1)

        direction_idx = np.argmax(probs[0])
        directions = ["LONG", "SHORT", "NEUTRAL"]

        return TransformerPrediction(
            direction=directions[direction_idx],
            confidence=float(probs[0, direction_idx]),
            attention_weights=np.array(attention_weights),
            predicted_return=0.0
        )

    def predict(self, features: np.ndarray) -> TransformerPrediction:
        return self.forward(features)
