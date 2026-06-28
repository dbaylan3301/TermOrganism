# plugins/scalpbot/ai/deep_learning/attention.py
"""Multi-head attention mechanism."""

import numpy as np
from typing import Optional


class MultiHeadAttention:
    """Multi-head self-attention mechanism."""

    def __init__(self, d_model: int = 64, num_heads: int = 4, dropout: float = 0.1):
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        self.dropout = dropout

        self.W_q = np.random.randn(d_model, d_model) * 0.01
        self.W_k = np.random.randn(d_model, d_model) * 0.01
        self.W_v = np.random.randn(d_model, d_model) * 0.01
        self.W_o = np.random.randn(d_model, d_model) * 0.01

    def softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

    def split_heads(self, x: np.ndarray) -> np.ndarray:
        batch_size, seq_len, _ = x.shape
        x = x.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        return x.transpose(0, 2, 1, 3)

    def forward(self, query: np.ndarray, key: np.ndarray,
                value: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        batch_size = query.shape[0]

        Q = np.dot(query, self.W_q)
        K = np.dot(key, self.W_k)
        V = np.dot(value, self.W_v)

        Q = self.split_heads(Q)
        K = self.split_heads(K)
        V = self.split_heads(V)

        scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / np.sqrt(self.d_k)

        if mask is not None:
            scores = scores + mask

        attention = self.softmax(scores)

        output = np.matmul(attention, V)

        output = output.transpose(0, 2, 1, 3).reshape(batch_size, -1, self.d_model)

        output = np.dot(output, self.W_o)

        return output


class TransformerBlock:
    """Single transformer encoder block."""

    def __init__(self, d_model: int = 64, num_heads: int = 4,
                 d_ff: int = 128, dropout: float = 0.1):
        self.attention = MultiHeadAttention(d_model, num_heads, dropout)
        self.norm1 = LayerNorm(d_model)
        self.norm2 = LayerNorm(d_model)
        self.ff = FeedForward(d_model, d_ff, dropout)
        self.dropout = dropout

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        attended = self.attention.forward(x, x, x, mask)
        x = self.norm1.forward(x + attended)

        fed = self.ff.forward(x)
        x = self.norm2.forward(x + fed)

        return x


class LayerNorm:
    """Layer normalization."""

    def __init__(self, d_model: int, eps: float = 1e-6):
        self.gamma = np.ones(d_model)
        self.beta = np.zeros(d_model)
        self.eps = eps

    def forward(self, x: np.ndarray) -> np.ndarray:
        mean = np.mean(x, axis=-1, keepdims=True)
        std = np.std(x, axis=-1, keepdims=True)
        return self.gamma * (x - mean) / (std + self.eps) + self.beta


class FeedForward:
    """Feed-forward network."""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        self.w1 = np.random.randn(d_model, d_ff) * 0.01
        self.w2 = np.random.randn(d_ff, d_model) * 0.01
        self.dropout = dropout

    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> np.ndarray:
        return np.dot(self.relu(np.dot(x, self.w1)), self.w2)
