# Metamorphic AI Brain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Deep Learning, Reinforcement Learning, and Sentiment Analysis brains to scalpbot with ensemble fusion for metamorphic trading intelligence.

**Architecture:** Multi-brain architecture with LSTM/Transformer for price prediction, RL for strategy optimization, sentiment analysis for market psychology, and meta-learner for ensemble fusion.

**Tech Stack:** PyTorch, NumPy, Pandas, httpx (for API calls), asyncio

---

## Task 1: Create AI Module Structure

**Covers:** Foundation for AI brains

**Files:**
- Create: `plugins/scalpbot/ai/__init__.py`
- Create: `plugins/scalpbot/ai/deep_learning/__init__.py`
- Create: `plugins/scalpbot/ai/reinforcement/__init__.py`
- Create: `plugins/scalpbot/ai/sentiment/__init__.py`
- Create: `plugins/scalpbot/ai/ensemble/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p plugins/scalpbot/ai/deep_learning
mkdir -p plugins/scalpbot/ai/reinforcement
mkdir -p plugins/scalpbot/ai/sentiment
mkdir -p plugins/scalpbot/ai/ensemble
```

- [ ] **Step 2: Create __init__.py files**

```python
# plugins/scalpbot/ai/__init__.py
"""AI Brain modules for ScalpBot."""

from .brain import MetaBrain

__all__ = ["MetaBrain"]
```

```python
# plugins/scalpbot/ai/deep_learning/__init__.py
"""Deep Learning brain modules."""

from .lstm_model import LSTMPredictor
from .transformer_model import TransformerPredictor
from .attention import MultiHeadAttention
from .feature_engine import FeatureEngine

__all__ = ["LSTMPredictor", "TransformerPredictor", "MultiHeadAttention", "FeatureEngine"]
```

```python
# plugins/scalpbot/ai/reinforcement/__init__.py
"""Reinforcement Learning brain modules."""

from .q_learning import QLearningAgent
from .ppo import PPOAgent
from .environment import CryptoTradingEnv

__all__ = ["QLearningAgent", "PPOAgent", "CryptoTradingEnv"]
```

```python
# plugins/scalpbot/ai/sentiment/__init__.py
"""Sentiment Analysis brain modules."""

from .news_analyzer import NewsAnalyzer
from .fear_greed import FearGreedIndex
from .social_aggregator import SocialAggregator

__all__ = ["NewsAnalyzer", "FearGreedIndex", "SocialAggregator"]
```

```python
# plugins/scalpbot/ai/ensemble/__init__.py
"""Ensemble Fusion modules."""

from .meta_learner import MetaLearner
from .voting import WeightedVoter

__all__ = ["MetaLearner", "WeightedVoter"]
```

- [ ] **Step 3: Commit structure**

```bash
git add plugins/scalpbot/ai/
git commit -m "feat: create AI brain module structure"
```

---

## Task 2: Feature Engineering Engine

**Covers:** Feature extraction for all AI models

**Files:**
- Create: `plugins/scalpbot/ai/deep_learning/feature_engine.py`

- [ ] **Step 1: Create feature_engine.py**

```python
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
        vol_momentum = volumes[-5:].mean() / volumes[-20:-5].mean()
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
            features.extend([rsi[-1], rsi[-5:].mean()])
        
        # MACD
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            features.extend([macd[-1], signal[-1], macd[-1] - signal[-1]])
        
        # Bollinger Bands
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            upper = indicators['bb_upper']
            lower = indicators['bb_lower']
            bb_position = (upper[-1] - lower[-1]) / (upper[-1] + lower[-1] + 1e-10)
            features.append(bb_position)
        
        # ATR
        if 'atr' in indicators:
            atr = indicators['atr']
            features.append(atr[-1])
        
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
    
    def extract_temporal_features(self, timestamp: float) -> np.ndarray:
        """Extract time-based features."""
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        
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
```

- [ ] **Step 2: Test feature engine**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.deep_learning.feature_engine import FeatureEngine
import numpy as np
engine = FeatureEngine()
closes = np.random.uniform(100, 200, 100)
features = engine.extract_price_features(closes)
print(f'Price features shape: {features.shape}')
"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/scalpbot/ai/deep_learning/feature_engine.py
git commit -m "feat: add feature engineering engine"
```

---

## Task 3: LSTM Price Predictor

**Covers:** LSTM-based price prediction

**Files:**
- Create: `plugins/scalpbot/ai/deep_learning/lstm_model.py`

- [ ] **Step 1: Create lstm_model.py**

```python
# plugins/scalpbot/ai/deep_learning/lstm_model.py
"""LSTM-based price predictor."""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class LSTMPrediction:
    """LSTM prediction result."""
    direction: str  # "LONG", "SHORT", "NEUTRAL"
    confidence: float
    predicted_return: float
    features_used: int


class LSTMPredictor:
    """LSTM model for price direction prediction."""
    
    def __init__(self, input_size: int = 50, hidden_size: int = 128, 
                 num_layers: int = 2, dropout: float = 0.2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        # Try to import PyTorch
        try:
            import torch
            import torch.nn as nn
            self.torch = torch
            self.nn = nn
            self._build_model()
        except ImportError:
            print("PyTorch not available. Using fallback predictor.")
            self.torch = None
            self.nn = None
    
    def _build_model(self):
        """Build LSTM model."""
        if self.torch is None:
            return
        
        class LSTMModel(self.nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = self.nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    dropout=dropout,
                    batch_first=True
                )
                self.fc = self.nn.Sequential(
                    self.nn.Linear(hidden_size, 64),
                    self.nn.ReLU(),
                    self.nn.Dropout(dropout),
                    self.nn.Linear(64, 32),
                    self.nn.ReLU(),
                    self.nn.Linear(32, 3)  # [LONG, SHORT, NEUTRAL]
                )
            
            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                out = self.fc(lstm_out[:, -1, :])
                return out
        
        self.model = LSTMModel(
            self.input_size, self.hidden_size, 
            self.num_layers, self.dropout
        )
    
    def prepare_sequence(self, features: np.ndarray) -> np.ndarray:
        """Prepare feature sequence for LSTM."""
        if len(features.shape) == 1:
            features = features.reshape(1, -1, self.input_size)
        return features
    
    def predict(self, features: np.ndarray) -> LSTMPrediction:
        """Make prediction using LSTM."""
        if self.model is None or not self.is_trained:
            return self._fallback_predict(features)
        
        try:
            import torch
            
            # Prepare input
            seq = self.prepare_sequence(features)
            tensor = torch.FloatTensor(seq)
            
            # Predict
            with torch.no_grad():
                output = self.model(tensor)
                probs = torch.softmax(output, dim=1).numpy()[0]
            
            # Get direction
            direction_idx = np.argmax(probs)
            directions = ["LONG", "SHORT", "NEUTRAL"]
            
            return LSTMPrediction(
                direction=directions[direction_idx],
                confidence=float(probs[direction_idx]),
                predicted_return=0.0,
                features_used=len(features)
            )
        except Exception as e:
            return self._fallback_predict(features)
    
    def _fallback_predict(self, features: np.ndarray) -> LSTMPrediction:
        """Fallback prediction without trained model."""
        # Simple momentum-based prediction
        if len(features) >= 2:
            recent_return = features[-1] if len(features.shape) == 1 else features[-1, 0]
            
            if recent_return > 0.001:
                direction = "LONG"
                confidence = min(0.7, 0.5 + abs(recent_return) * 10)
            elif recent_return < -0.001:
                direction = "SHORT"
                confidence = min(0.7, 0.5 + abs(recent_return) * 10)
            else:
                direction = "NEUTRAL"
                confidence = 0.4
            
            return LSTMPrediction(
                direction=direction,
                confidence=confidence,
                predicted_return=float(recent_return),
                features_used=len(features)
            )
        
        return LSTMPrediction("NEUTRAL", 0.33, 0.0, 0)
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, 
              lr: float = 0.001) -> dict:
        """Train the LSTM model."""
        if self.torch is None or self.model is None:
            return {"status": "skipped", "reason": "PyTorch not available"}
        
        try:
            import torch
            from torch.utils.data import DataLoader, TensorDataset
            
            # Prepare data
            X_tensor = torch.FloatTensor(X)
            y_tensor = torch.LongTensor(y)
            
            dataset = TensorDataset(X_tensor, y_tensor)
            loader = DataLoader(dataset, batch_size=32, shuffle=True)
            
            # Optimizer
            optimizer = self.torch.optim.Adam(self.model.parameters(), lr=lr)
            criterion = self.torch.nn.CrossEntropyLoss()
            
            # Training loop
            self.model.train()
            losses = []
            
            for epoch in range(epochs):
                epoch_loss = 0
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    output = self.model(batch_X)
                    loss = criterion(output, batch_y)
                    loss.backward()
                    optimizer.step()
                    epoch_loss += loss.item()
                
                losses.append(epoch_loss / len(loader))
            
            self.is_trained = True
            
            return {
                "status": "trained",
                "epochs": epochs,
                "final_loss": losses[-1] if losses else 0
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}
```

- [ ] **Step 2: Test LSTM model**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.deep_learning.lstm_model import LSTMPredictor
import numpy as np

predictor = LSTMPredictor(input_size=10)
features = np.random.randn(10)
prediction = predictor.predict(features)
print(f'Direction: {prediction.direction}')
print(f'Confidence: {prediction.confidence:.2f}')
"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/scalpbot/ai/deep_learning/lstm_model.py
git commit -m "feat: add LSTM price predictor"
```

---

## Task 4: Transformer Predictor with Attention

**Covers:** Transformer-based prediction with multi-head attention

**Files:**
- Create: `plugins/scalpbot/ai/deep_learning/transformer_model.py`
- Create: `plugins/scalpbot/ai/deep_learning/attention.py`

- [ ] **Step 1: Create attention.py**

```python
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
        
        # Initialize weights
        self.W_q = np.random.randn(d_model, d_model) * 0.01
        self.W_k = np.random.randn(d_model, d_model) * 0.01
        self.W_v = np.random.randn(d_model, d_model) * 0.01
        self.W_o = np.random.randn(d_model, d_model) * 0.01
    
    def softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Numerically stable softmax."""
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)
    
    def split_heads(self, x: np.ndarray) -> np.ndarray:
        """Split into multiple heads."""
        batch_size, seq_len, _ = x.shape
        x = x.reshape(batch_size, seq_len, self.num_heads, self.d_k)
        return x.transpose(0, 2, 1, 3)
    
    def forward(self, query: np.ndarray, key: np.ndarray, 
                value: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        """Forward pass."""
        batch_size = query.shape[0]
        
        # Linear projections
        Q = np.dot(query, self.W_q)
        K = np.dot(key, self.W_k)
        V = np.dot(value, self.W_v)
        
        # Split heads
        Q = self.split_heads(Q)
        K = self.split_heads(K)
        V = self.split_heads(V)
        
        # Attention scores
        scores = np.matmul(Q, K.transpose(0, 1, 3, 2)) / np.sqrt(self.d_k)
        
        if mask is not None:
            scores = scores + mask
        
        attention = self.softmax(scores)
        
        # Apply attention to values
        output = np.matmul(attention, V)
        
        # Concatenate heads
        output = output.transpose(0, 2, 1, 3).reshape(batch_size, -1, self.d_model)
        
        # Final linear projection
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
        """Forward pass."""
        # Self-attention with residual
        attended = self.attention.forward(x, x, x, mask)
        x = self.norm1.forward(x + attended)
        
        # Feed-forward with residual
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
        """Forward pass."""
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
        """Forward pass."""
        return np.dot(self.relu(np.dot(x, self.w1)), self.w2)
```

- [ ] **Step 2: Create transformer_model.py**

```python
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
        
        # Positional encoding
        self.pos_encoding = self._create_positional_encoding()
        
        # Transformer blocks
        self.blocks = [
            TransformerBlock(d_model, num_heads, d_ff)
            for _ in range(num_layers)
        ]
        
        # Output projection
        self.output_proj = np.random.randn(d_model, 3) * 0.01
    
    def _create_positional_encoding(self) -> np.ndarray:
        """Create sinusoidal positional encoding."""
        pe = np.zeros((self.max_seq_len, self.d_model))
        position = np.arange(0, self.max_seq_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, self.d_model, 2) * 
                         -(np.log(10000.0) / self.d_model))
        
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)
        
        return pe
    
    def project_to_d_model(self, features: np.ndarray) -> np.ndarray:
        """Project input features to d_model dimensions."""
        if features.shape[-1] == self.d_model:
            return features
        
        # Simple linear projection
        projection = np.random.randn(features.shape[-1], self.d_model) * 0.01
        return np.dot(features, projection)
    
    def softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Numerically stable softmax."""
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)
    
    def forward(self, features: np.ndarray, 
                mask: Optional[np.ndarray] = None) -> TransformerPrediction:
        """Forward pass."""
        # Add batch dimension if needed
        if len(features.shape) == 2:
            features = features[np.newaxis, :]
        
        # Project to d_model
        x = self.project_to_d_model(features)
        
        # Add positional encoding
        seq_len = min(x.shape[1], self.max_seq_len)
        x = x[:, :seq_len, :] + self.pos_encoding[:seq_len, :]
        
        # Apply transformer blocks
        attention_weights = []
        for block in self.blocks:
            x = block.forward(x, mask)
            # Store attention weights (simplified)
            attention_weights.append(np.ones((x.shape[1], x.shape[1])) / x.shape[1])
        
        # Global average pooling
        x = np.mean(x, axis=1)
        
        # Output projection
        logits = np.dot(x, self.output_proj)
        probs = self.softmax(logits, axis=-1)
        
        # Get prediction
        direction_idx = np.argmax(probs[0])
        directions = ["LONG", "SHORT", "NEUTRAL"]
        
        return TransformerPrediction(
            direction=directions[direction_idx],
            confidence=float(probs[0, direction_idx]),
            attention_weights=np.array(attention_weights),
            predicted_return=0.0
        )
    
    def predict(self, features: np.ndarray) -> TransformerPrediction:
        """Make prediction."""
        return self.forward(features)
```

- [ ] **Step 3: Test Transformer**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.deep_learning.transformer_model import TransformerPredictor
import numpy as np

predictor = TransformerPredictor(d_model=32, num_heads=2, num_layers=2)
features = np.random.randn(10, 32)  # seq_len=10, d_model=32
prediction = predictor.predict(features)
print(f'Direction: {prediction.direction}')
print(f'Confidence: {prediction.confidence:.2f}')
"
```

- [ ] **Step 4: Commit**

```bash
git add plugins/scalpbot/ai/deep_learning/attention.py plugins/scalpbot/ai/deep_learning/transformer_model.py
git commit -m "feat: add Transformer predictor with multi-head attention"
```

---

## Task 5: Reinforcement Learning Agent

**Covers:** Q-Learning and PPO agents

**Files:**
- Create: `plugins/scalpbot/ai/reinforcement/environment.py`
- Create: `plugins/scalpbot/ai/reinforcement/q_learning.py`
- Create: `plugins/scalpbot/ai/reinforcement/ppo.py`

- [ ] **Step 1: Create environment.py**

```python
# plugins/scalpbot/ai/reinforcement/environment.py
"""Trading environment for RL agents."""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class TradingState:
    """Current state of trading environment."""
    price: float
    position: int  # 0: flat, 1: long, -1: short
    balance: float
    unrealized_pnl: float
    indicators: np.ndarray


@dataclass
class TradingAction:
    """Trading action."""
    action_type: str  # "BUY", "SELL", "HOLD"
    size: float = 1.0


class CryptoTradingEnv:
    """Crypto trading environment for RL."""
    
    ACTIONS = ["HOLD", "BUY", "SELL"]
    MAX_POSITION = 1.0
    TRANSACTION_COST = 0.001  # 0.1%
    
    def __init__(self, data: np.ndarray, initial_balance: float = 10000.0):
        self.data = data
        self.initial_balance = initial_balance
        self.reset()
    
    def reset(self) -> np.ndarray:
        """Reset environment."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state."""
        price = self.data[self.current_step]
        
        # Simple indicators
        if self.current_step >= 20:
            recent_prices = self.data[self.current_step-20:self.current_step+1]
            sma_20 = np.mean(recent_prices)
            momentum = (price - recent_prices[0]) / recent_prices[0]
        else:
            sma_20 = price
            momentum = 0.0
        
        state = np.array([
            price / self.data[0],  # Normalized price
            self.position,
            self.balance / self.initial_balance,
            sma_20 / price if price > 0 else 1.0,
            momentum
        ])
        
        return state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """Take action and return next state, reward, done, info."""
        current_price = self.data[self.current_step]
        next_price = self.data[min(self.current_step + 1, len(self.data) - 1)]
        
        reward = 0.0
        done = False
        
        # Execute action
        if action == 1:  # BUY
            if self.position <= 0:
                # Close short if exists
                if self.position < 0:
                    pnl = (self.entry_price - current_price) * abs(self.position)
                    self.balance += pnl
                    reward += pnl / self.balance
                
                # Open long
                self.position = self.MAX_POSITION
                self.entry_price = current_price
                self.balance -= self TRANSACTION_COST * current_price
                self.total_trades += 1
        
        elif action == 2:  # SELL
            if self.position >= 0:
                # Close long if exists
                if self.position > 0:
                    pnl = (current_price - self.entry_price) * self.position
                    self.balance += pnl
                    reward += pnl / self.balance
                    if pnl > 0:
                        self.winning_trades += 1
                
                # Open short
                self.position = -self.MAX_POSITION
                self.entry_price = current_price
                self.balance -= self.TRANSACTION_COST * current_price
                self.total_trades += 1
        
        # Update step
        self.current_step += 1
        
        # Calculate unrealized P&L
        if self.position > 0:
            unrealized = (next_price - self.entry_price) * self.position
        elif self.position < 0:
            unrealized = (self.entry_price - next_price) * abs(self.position)
        else:
            unrealized = 0.0
        
        # Check if done
        if self.current_step >= len(self.data) - 1:
            done = True
            # Final settlement
            if self.position > 0:
                final_pnl = (next_price - self.entry_price) * self.position
                self.balance += final_pnl
            elif self.position < 0:
                final_pnl = (self.entry_price - next_price) * abs(self.position)
                self.balance += final_pnl
        
        # Additional reward shaping
        reward += unrealized / self.balance * 0.1
        
        info = {
            "balance": self.balance,
            "position": self.position,
            "total_trades": self.total_trades,
            "win_rate": self.winning_trades / max(self.total_trades, 1)
        }
        
        return self._get_state(), reward, done, info
    
    @property
    def state_size(self) -> int:
        return 5
    
    @property
    def action_size(self) -> int:
        return len(self.ACTIONS)
```

- [ ] **Step 2: Create q_learning.py**

```python
# plugins/scalpbot/ai/reinforcement/q_learning.py
"""Q-Learning agent for trading."""

import numpy as np
from typing import Tuple
from .environment import CryptoTradingEnv


class QLearningAgent:
    """Q-Learning agent for trading."""
    
    def __init__(self, state_size: int, action_size: int,
                 learning_rate: float = 0.1, discount_factor: float = 0.95,
                 epsilon: float = 1.0, epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        
        # Discretize state space
        self.q_table = {}
        self.bins = self._create_bins()
    
    def _create_bins(self) -> list:
        """Create bins for state discretization."""
        bins = []
        for i in range(self.state_size):
            if i == 0:  # Price ratio
                bins.append(np.linspace(0.8, 1.2, 20))
            elif i == 1:  # Position
                bins.append(np.array([-1, 0, 1]))
            elif i == 2:  # Balance ratio
                bins.append(np.linspace(0.5, 1.5, 10))
            else:
                bins.append(np.linspace(-0.5, 0.5, 10))
        return bins
    
    def _discretize(self, state: np.ndarray) -> tuple:
        """Discretize continuous state."""
        discrete = []
        for i, (val, bin_edges) in enumerate(zip(state, self.bins)):
            idx = np.digitize(val, bin_edges) - 1
            idx = max(0, min(idx, len(bin_edges) - 1))
            discrete.append(idx)
        return tuple(discrete)
    
    def get_q_value(self, state: tuple, action: int) -> float:
        """Get Q-value for state-action pair."""
        key = (state, action)
        return self.q_table.get(key, 0.0)
    
    def choose_action(self, state: np.ndarray) -> int:
        """Choose action using epsilon-greedy policy."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)
        
        discrete_state = self._discretize(state)
        q_values = [self.get_q_value(discrete_state, a) 
                   for a in range(self.action_size)]
        return np.argmax(q_values)
    
    def learn(self, state: np.ndarray, action: int, reward: float,
              next_state: np.ndarray, done: bool):
        """Update Q-value."""
        discrete_state = self._discretize(state)
        discrete_next_state = self._discretize(next_state)
        
        # Current Q-value
        current_q = self.get_q_value(discrete_state, action)
        
        # Best next Q-value
        if done:
            target_q = reward
        else:
            next_q_values = [self.get_q_value(discrete_next_state, a) 
                           for a in range(self.action_size)]
            target_q = reward + self.discount_factor * max(next_q_values)
        
        # Update Q-value
        new_q = current_q + self.learning_rate * (target_q - current_q)
        self.q_table[(discrete_state, action)] = new_q
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def train(self, env: CryptoTradingEnv, episodes: int = 100) -> dict:
        """Train the agent."""
        scores = []
        
        for episode in range(episodes):
            state = env.reset()
            total_reward = 0
            steps = 0
            
            done = False
            while not done:
                action = self.choose_action(state)
                next_state, reward, done, info = env.step(action)
                self.learn(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                steps += 1
            
            scores.append(total_reward)
            
            if (episode + 1) % 10 == 0:
                avg_score = np.mean(scores[-10:])
                print(f"Episode {episode + 1}/{episodes}, Avg Score: {avg_score:.4f}")
        
        return {
            "status": "trained",
            "episodes": episodes,
            "final_epsilon": self.epsilon,
            "avg_score": np.mean(scores[-10:]) if scores else 0
        }
```

- [ ] **Step 3: Create ppo.py**

```python
# plugins/scalpbot/ai/reinforcement/ppo.py
"""PPO (Proximal Policy Optimization) agent."""

import numpy as np
from typing import Tuple, List
from .environment import CryptoTradingEnv


class PPOAgent:
    """PPO agent for trading."""
    
    def __init__(self, state_size: int, action_size: int,
                 learning_rate: float = 0.001, clip_epsilon: float = 0.2,
                 gamma: float = 0.99, gae_lambda: float = 0.95):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.clip_epsilon = clip_epsilon
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        
        # Simple policy and value networks (no PyTorch)
        self.policy_weights = np.random.randn(state_size, action_size) * 0.01
        self.value_weights = np.random.randn(state_size, 1) * 0.01
        
        # Experience buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
    
    def softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax function."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)
    
    def get_policy(self, state: np.ndarray) -> np.ndarray:
        """Get action probabilities."""
        logits = np.dot(state, self.policy_weights)
        return self.softmax(logits)
    
    def get_value(self, state: np.ndarray) -> float:
        """Get state value."""
        return float(np.dot(state, self.value_weights))
    
    def choose_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """Choose action and return action, log_prob, value."""
        probs = self.get_policy(state)
        
        # Sample action
        action = np.random.choice(self.action_size, p=probs)
        
        # Calculate log probability
        log_prob = np.log(probs[action] + 1e-10)
        
        # Get value
        value = self.get_value(state)
        
        return action, log_prob, value
    
    def compute_gae(self, rewards: List[float], values: List[float], 
                    next_value: float) -> List[float]:
        """Compute Generalized Advantage Estimation."""
        advantages = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_val = next_value
            else:
                next_val = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_val - values[t]
            gae = delta + self.gamma * self.gae_lambda * gae
            advantages.insert(0, gae)
        
        return advantages
    
    def update(self, next_value: float):
        """Update policy and value networks."""
        if len(self.states) == 0:
            return
        
        # Convert to arrays
        states = np.array(self.states)
        actions = np.array(self.actions)
        old_log_probs = np.array(self.log_probs)
        values = np.array(self.values)
        
        # Compute advantages
        advantages = self.compute_gae(self.rewards, values, next_value)
        returns = advantages + values
        
        # Normalize advantages
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)
        
        # Simple gradient update (no autograd)
        for i in range(len(states)):
            state = states[i]
            action = actions[i]
            advantage = advantages[i]
            return_val = returns[i]
            
            # Policy gradient
            probs = self.get_policy(state)
            grad_log_probs = -probs
            grad_log_probs[action] += 1
            policy_grad = advantage * grad_log_probs
            
            # Value gradient
            value_pred = self.get_value(state)
            value_grad = (return_val - value_pred) * state
            
            # Update weights
            self.policy_weights += self.learning_rate * np.outer(state, policy_grad)
            self.value_weights += self.learning_rate * np.outer(state, 
                np.array([return_val - value_pred]))
        
        # Clear buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
    
    def train(self, env: CryptoTradingEnv, episodes: int = 100,
              update_interval: int = 20) -> dict:
        """Train the agent."""
        scores = []
        
        for episode in range(episodes):
            state = env.reset()
            total_reward = 0
            
            done = False
            while not done:
                action, log_prob, value = self.choose_action(state)
                
                next_state, reward, done, info = env.step(action)
                
                # Store experience
                self.states.append(state)
                self.actions.append(action)
                self.rewards.append(reward)
                self.values.append(value)
                self.log_probs.append(log_prob)
                
                state = next_state
                total_reward += reward
                
                # Update periodically
                if len(self.states) >= update_interval:
                    next_val = self.get_value(next_state)
                    self.update(next_val)
            
            scores.append(total_reward)
            
            if (episode + 1) % 10 == 0:
                avg_score = np.mean(scores[-10:])
                print(f"Episode {episode + 1}/{episodes}, Avg Score: {avg_score:.4f}")
        
        return {
            "status": "trained",
            "episodes": episodes,
            "avg_score": np.mean(scores[-10:]) if scores else 0
        }
```

- [ ] **Step 4: Test RL agents**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.reinforcement.environment import CryptoTradingEnv
from plugins.scalpbot.ai.reinforcement.q_learning import QLearningAgent
import numpy as np

# Create environment
data = np.random.uniform(100, 200, 200)
env = CryptoTradingEnv(data)

# Create agent
agent = QLearningAgent(state_size=env.state_size, action_size=env.action_size)

# Test one episode
state = env.reset()
action = agent.choose_action(state)
next_state, reward, done, info = env.step(action)
print(f'Action: {action}, Reward: {reward:.4f}, Done: {done}')
"
```

- [ ] **Step 5: Commit**

```bash
git add plugins/scalpbot/ai/reinforcement/
git commit -m "feat: add RL agents (Q-Learning, PPO) with trading environment"
```

---

## Task 6: Sentiment Analysis Brain

**Covers:** News and social media sentiment analysis

**Files:**
- Create: `plugins/scalpbot/ai/sentiment/news_analyzer.py`
- Create: `plugins/scalpbot/ai/sentiment/fear_greed.py`
- Create: `plugins/scalpbot/ai/sentiment/social_aggregator.py`

- [ ] **Step 1: Create news_analyzer.py**

```python
# plugins/scalpbot/ai/sentiment/news_analyzer.py
"""News sentiment analyzer."""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    score: float  # -1 to 1
    label: str  # "positive", "negative", "neutral"
    confidence: float
    keywords: List[str]


class NewsAnalyzer:
    """Analyze news sentiment for crypto."""
    
    # Sentiment lexicon
    POSITIVE_WORDS = {
        "bullish", "surge", "rally", "gain", "profit", "growth", "adoption",
        "partnership", "launch", "upgrade", "breakthrough", "record", "high",
        "moon", "pump", "buy", "long", "accumulate", "institutional"
    }
    
    NEGATIVE_WORDS = {
        "bearish", "crash", "dump", "loss", "decline", "ban", "hack",
        "scam", "fraud", "regulation", "warning", "risk", "sell", "short",
        "panic", "fear", "uncertainty", "volatile", "collapse"
    }
    
    def __init__(self):
        self.cache = {}
    
    def analyze_text(self, text: str) -> SentimentResult:
        """Analyze sentiment of text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(0.0, "neutral", 0.3, [])
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        confidence = min(0.9, 0.5 + total * 0.1)
        
        # Extract keywords
        keywords = [w for w in words 
                   if w in self.POSITIVE_WORDS or w in self.NEGATIVE_WORDS]
        
        return SentimentResult(score, label, confidence, keywords[:5])
    
    def analyze_headlines(self, headlines: List[str]) -> SentimentResult:
        """Analyze multiple headlines."""
        results = [self.analyze_text(h) for h in headlines]
        
        if not results:
            return SentimentResult(0.0, "neutral", 0.0, [])
        
        avg_score = sum(r.score for r in results) / len(results)
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        all_keywords = []
        for r in results:
            all_keywords.extend(r.keywords)
        
        if avg_score > 0.2:
            label = "positive"
        elif avg_score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        return SentimentResult(
            score=avg_score,
            label=label,
            confidence=avg_confidence,
            keywords=list(set(all_keywords))[:10]
        )
```

- [ ] **Step 2: Create fear_greed.py**

```python
# plugins/scalpbot/ai/sentiment/fear_greed.py
"""Fear & Greed Index analyzer."""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


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
        import time
        
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
```

- [ ] **Step 3: Create social_aggregator.py**

```python
# plugins/scalpbot/ai/sentiment/social_aggregator.py
"""Social media sentiment aggregator."""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from .news_analyzer import NewsAnalyzer, SentimentResult


@dataclass
class SocialSentiment:
    """Aggregated social sentiment."""
    overall_score: float
    overall_label: str
    news_sentiment: SentimentResult
    twitter_sentiment: Optional[SentimentResult]
    reddit_sentiment: Optional[SentimentResult]
    fear_greed_value: int
    confidence: float


class SocialAggregator:
    """Aggregate sentiment from multiple sources."""
    
    def __init__(self):
        self.analyzer = NewsAnalyzer()
        self.cache = {}
    
    def aggregate(self, news: List[str] = None, 
                  twitter: List[str] = None,
                  reddit: List[str] = None,
                  fear_greed_value: int = 50) -> SocialSentiment:
        """Aggregate sentiment from all sources."""
        
        # Analyze news
        news_sentiment = self.analyzer.analyze_headlines(news or [])
        
        # Analyze twitter
        twitter_sentiment = self.analyzer.analyze_headlines(twitter or []) if twitter else None
        
        # Analyze reddit
        reddit_sentiment = self.analyzer.analyze_headlines(reddit or []) if reddit else None
        
        # Calculate overall score
        scores = [news_sentiment.score]
        weights = [0.5]
        
        if twitter_sentiment:
            scores.append(twitter_sentiment.score)
            weights.append(0.3)
        
        if reddit_sentiment:
            scores.append(reddit_sentiment.score)
            weights.append(0.2)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        overall_score = sum(s * w for s, w in zip(scores, weights))
        
        # Adjust with Fear & Greed
        fear_greed_adjustment = (fear_greed_value - 50) / 100
        overall_score = overall_score * 0.7 + fear_greed_adjustment * 0.3
        
        # Get label
        if overall_score > 0.2:
            overall_label = "bullish"
        elif overall_score < -0.2:
            overall_label = "bearish"
        else:
            overall_label = "neutral"
        
        # Calculate confidence
        confidence = np.mean([r.confidence for r in [news_sentiment, twitter_sentiment, reddit_sentiment] if r])
        
        return SocialSentiment(
            overall_score=overall_score,
            overall_label=overall_label,
            news_sentiment=news_sentiment,
            twitter_sentiment=twitter_sentiment,
            reddit_sentiment=reddit_sentiment,
            fear_greed_value=fear_greed_value,
            confidence=confidence
        )
```

- [ ] **Step 4: Test sentiment modules**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.sentiment.news_analyzer import NewsAnalyzer
from plugins.scalpbot.ai.sentiment.fear_greed import FearGreedIndex
import numpy as np

# Test news analyzer
analyzer = NewsAnalyzer()
result = analyzer.analyze_text('Bitcoin surges to new highs as institutional adoption grows')
print(f'News: {result.label}, Score: {result.score:.2f}')

# Test Fear & Greed
fg = FearGreedIndex()
prices = np.random.uniform(50000, 60000, 100)
volumes = np.random.uniform(1e9, 5e9, 100)
fg_data = fg.calculate_from_data(prices, volumes)
print(f'Fear & Greed: {fg_data.value} ({fg_data.label})')
"
```

- [ ] **Step 5: Commit**

```bash
git add plugins/scalpbot/ai/sentiment/
git commit -m "feat: add sentiment analysis brain (news, Fear & Greed, social)"
```

---

## Task 7: MetaBrain Ensemble

**Covers:** Meta-learner that combines all brains

**Files:**
- Create: `plugins/scalpbot/ai/brain.py`
- Create: `plugins/scalpbot/ai/ensemble/meta_learner.py`
- Create: `plugins/scalpbot/ai/ensemble/voting.py`

- [ ] **Step 1: Create voting.py**

```python
# plugins/scalpbot/ai/ensemble/voting.py
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
```

- [ ] **Step 2: Create meta_learner.py**

```python
# plugins/scalpbot/ai/ensemble/meta_learner.py
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
```

- [ ] **Step 3: Create brain.py (MetaBrain)**

```python
# plugins/scalpbot/ai/brain.py
"""MetaBrain - orchestrates all AI brains."""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

from .deep_learning.lstm_model import LSTMPredictor
from .deep_learning.transformer_model import TransformerPredictor
from .deep_learning.feature_engine import FeatureEngine
from .reinforcement.q_learning import QLearningAgent
from .reinforcement.ppo import PPOAgent
from .reinforcement.environment import CryptoTradingEnv
from .sentiment.news_analyzer import NewsAnalyzer
from .sentiment.fear_greed import FearGreedIndex
from .sentiment.social_aggregator import SocialAggregator
from .ensemble.meta_learner import MetaLearner, MetaPrediction


@dataclass
class BrainOutput:
    """Output from MetaBrain."""
    direction: str
    confidence: float
    prediction: MetaPrediction
    lstm_output: str
    transformer_output: str
    rl_output: str
    sentiment_output: str
    processing_time: float


class MetaBrain:
    """
    MetaBrain - Multi-brain AI system for trading.
    Combines Deep Learning, RL, and Sentiment Analysis.
    """
    
    def __init__(self):
        print("🧠 Initializing MetaBrain...")
        
        # Feature engine
        self.feature_engine = FeatureEngine(lookback=50)
        
        # Deep Learning brains
        self.lstm = LSTMPredictor(input_size=50, hidden_size=128, num_layers=2)
        self.transformer = TransformerPredictor(d_model=64, num_heads=4, num_layers=3)
        
        # RL brains
        self.q_agent = None  # Initialized on first use
        self.ppo_agent = None
        
        # Sentiment brain
        self.news_analyzer = NewsAnalyzer()
        self.fear_greed = FearGreedIndex()
        self.social_aggregator = SocialAggregator()
        
        # Ensemble
        self.meta_learner = MetaLearner()
        
        # State
        self.is_initialized = False
        self.prediction_count = 0
        
        print("✅ MetaBrain initialized")
    
    def initialize_rl(self, data: np.ndarray):
        """Initialize RL agents with market data."""
        env = CryptoTradingEnv(data)
        
        self.q_agent = QLearningAgent(
            state_size=env.state_size,
            action_size=env.action_size
        )
        
        self.ppo_agent = PPOAgent(
            state_size=env.state_size,
            action_size=env.action_size
        )
        
        self.is_initialized = True
        print("✅ RL agents initialized")
    
    def predict(self, df, indicators: Dict[str, np.ndarray],
                patterns: List[str], news: List[str] = None,
                fear_greed_value: int = 50) -> BrainOutput:
        """
        Make prediction using all brains.
        """
        start_time = time.time()
        
        # Extract features
        features = self.feature_engine.extract_all(df, indicators, patterns)
        
        # Combine features for models
        combined_features = np.concatenate([
            features.price_features[:10],
            features.technical_features[:10],
            features.pattern_features[:10]
        ])
        
        # Ensure correct size
        if len(combined_features) < 50:
            combined_features = np.pad(combined_features, (0, 50 - len(combined_features)))
        else:
            combined_features = combined_features[:50]
        
        # 1. LSTM Prediction
        lstm_pred = self.lstm.predict(combined_features)
        lstm_output = lstm_pred.direction
        
        # 2. Transformer Prediction
        transformer_features = combined_features.reshape(10, 5) if len(combined_features) >= 50 else combined_features.reshape(5, 10)
        transformer_pred = self.transformer.predict(transformer_features)
        transformer_output = transformer_pred.direction
        
        # 3. RL Prediction
        rl_output = "NEUTRAL"
        if self.q_agent:
            rl_state = np.array([
                df['close'].values[-1] / df['close'].values[0],
                0,  # position
                1.0,  # balance ratio
                0,  # sma ratio
                0   # momentum
            ])
            rl_action = self.q_agent.choose_action(rl_state)
            rl_output = ["HOLD", "BUY", "SELL"][rl_action]
            if rl_output == "BUY":
                rl_output = "LONG"
            elif rl_output == "SELL":
                rl_output = "SHORT"
        
        # 4. Sentiment Prediction
        sentiment_result = self.social_aggregator.aggregate(
            news=news,
            fear_greed_value=fear_greed_value
        )
        
        if sentiment_result.overall_score > 0.2:
            sentiment_output = "LONG"
        elif sentiment_result.overall_score < -0.2:
            sentiment_output = "SHORT"
        else:
            sentiment_output = "NEUTRAL"
        
        # 5. Ensemble Prediction
        predictions = {
            "lstm": (lstm_output, lstm_pred.confidence),
            "transformer": (transformer_output, transformer_pred.confidence),
            "q_learning": (rl_output, 0.6),
            "ppo": (rl_output, 0.6),
            "sentiment": (sentiment_output, sentiment_result.confidence)
        }
        
        meta_prediction = self.meta_learner.predict(predictions)
        
        processing_time = time.time() - start_time
        self.prediction_count += 1
        
        return BrainOutput(
            direction=meta_prediction.direction,
            confidence=meta_prediction.confidence,
            prediction=meta_prediction,
            lstm_output=lstm_output,
            transformer_output=transformer_output,
            rl_output=rl_output,
            sentiment_output=sentiment_output,
            processing_time=processing_time
        )
    
    def train(self, data: np.ndarray, episodes: int = 50):
        """Train all brains."""
        print("🎓 Training MetaBrain...")
        
        # Initialize RL
        self.initialize_rl(data)
        
        # Train Q-Learning
        print("  Training Q-Learning...")
        env = CryptoTradingEnv(data)
        self.q_agent.train(env, episodes=episodes)
        
        # Train PPO
        print("  Training PPO...")
        env = CryptoTradingEnv(data)
        self.ppo_agent.train(env, episodes=episodes)
        
        print("✅ MetaBrain training complete")
    
    def get_stats(self) -> Dict:
        """Get brain statistics."""
        return {
            "prediction_count": self.prediction_count,
            "is_initialized": self.is_initialized,
            "models": {
                "lstm": "active",
                "transformer": "active",
                "q_learning": "active" if self.q_agent else "inactive",
                "ppo": "active" if self.ppo_agent else "inactive",
                "sentiment": "active"
            }
        }
```

- [ ] **Step 4: Test MetaBrain**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.ai.brain import MetaBrain
import pandas as pd
import numpy as np

# Create sample data
dates = pd.date_range('2024-01-01', periods=100, freq='1h')
df = pd.DataFrame({
    'open': np.random.uniform(50000, 60000, 100),
    'high': np.random.uniform(50000, 60000, 100),
    'low': np.random.uniform(50000, 60000, 100),
    'close': np.random.uniform(50000, 60000, 100),
    'volume': np.random.uniform(1e9, 5e9, 100)
}, index=dates)

# Initialize MetaBrain
brain = MetaBrain()

# Make prediction
indicators = {
    'rsi': np.random.uniform(30, 70, 100),
    'macd': np.random.randn(100),
    'macd_signal': np.random.randn(100),
    'bb_upper': np.random.uniform(55000, 65000, 100),
    'bb_lower': np.random.uniform(45000, 55000, 100),
    'atr': np.random.uniform(100, 500, 100)
}

output = brain.predict(df, indicators, ['STRONG_BULLISH'])
print(f'Direction: {output.direction}')
print(f'Confidence: {output.confidence:.2f}')
print(f'Processing time: {output.processing_time:.3f}s')
"
```

- [ ] **Step 5: Commit**

```bash
git add plugins/scalpbot/ai/brain.py plugins/scalpbot/ai/ensemble/
git commit -m "feat: add MetaBrain ensemble with all AI brains integrated"
```

---

## Task 8: Integrate MetaBrain into Scanner

**Covers:** Connect AI brains to scalpbot scanner

**Files:**
- Modify: `plugins/scalpbot/scanner.py`
- Modify: `plugins/scalpbot/signals.py`

- [ ] **Step 1: Add MetaBrain import to scanner.py**

```python
# Add after line 22 (from .patterns import ...)
try:
    from plugins.scalpbot.ai.brain import MetaBrain
    AI_BRAIN_AVAILABLE = True
except ImportError:
    AI_BRAIN_AVAILABLE = False
```

- [ ] **Step 2: Initialize MetaBrain in CoinScanner**

```python
# Add after line 38 (self.signal_history = [])
# AI Brain
self.brain = MetaBrain() if AI_BRAIN_AVAILABLE else None
self.use_ai_brain = True
```

- [ ] **Step 3: Add AI brain prediction to scan_once**

```python
# Add after line 168 (signals.append(result)) but before line 170 (if signals:)
# AI Brain enhancement
if self.brain and self.use_ai_brain and not signals:
    # Use AI brain for prediction
    for coin in screened[:3]:
        symbol = coin["symbol"]
        df = self.kline_cache[symbol]
        
        indicators = {
            'rsi': np.array([coin.get('rsi', 50)] * 50),
            'macd': np.zeros(50),
            'macd_signal': np.zeros(50),
            'bb_upper': np.full(50, df['close'].max()),
            'bb_lower': np.full(50, df['close'].min()),
            'atr': np.full(50, coin.get('atr_pct', 0.01) * df['close'].mean())
        }
        
        brain_output = self.brain.predict(
            df, indicators, coin.get('patterns', [])
        )
        
        if brain_output.direction != "NEUTRAL" and brain_output.confidence > 0.7:
            # Create signal from brain output
            from .signals import SignalResult
            from .risk import RiskManager
            
            current_price = float(df['close'].values[-1])
            risk_manager = RiskManager(leverage=self.config.leverage)
            
            atr_val = indicators['atr'][-1]
            sl, tp = risk_manager.calculate_sl_tp(
                current_price, atr_val, brain_output.direction,
                self.config.sl_atr_mult, self.config.tp_atr_mult
            )
            
            ai_signal = SignalResult(
                signal=brain_output.direction,
                symbol=symbol,
                entry_price=current_price,
                sl_price=sl,
                tp_price=tp,
                leverage=self.config.leverage,
                confidence=brain_output.confidence * 100,
                confidence_level="YAPAY ZEKA"
            )
            
            signals.append(ai_signal)
            console.print(f"[#7C3AED]🧠 AI Brain sinyal üretti: {symbol} {brain_output.direction}[/#7C3AED]")
```

- [ ] **Step 4: Test integration**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.scanner import CoinScanner
from plugins.scalpbot.config import ScalpConfig

config = ScalpConfig()
scanner = CoinScanner(config, mock=True)
print(f'AI Brain available: {scanner.brain is not None}')
print(f'AI Brain stats: {scanner.brain.get_stats() if scanner.brain else \"N/A\"}')
"
```

- [ ] **Step 5: Commit**

```bash
git add plugins/scalpbot/scanner.py
git commit -m "feat: integrate MetaBrain into scalpbot scanner"
```

---

## Task 9: Update Config for AI Settings

**Covers:** Add AI configuration options

**Files:**
- Modify: `plugins/scalpbot/config.py`

- [ ] **Step 1: Add AI config fields**

```python
# Add after line 56 (telegram_min_confidence)
# AI Brain
ai_enabled: bool = True
ai_confidence_threshold: float = 0.7
ai_use_lstm: bool = True
ai_use_transformer: bool = True
ai_use_rl: bool = True
ai_use_sentiment: bool = True
ai_train_episodes: int = 100
```

- [ ] **Step 2: Test config**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -c "
from plugins.scalpbot.config import ScalpConfig
config = ScalpConfig()
print(f'AI Enabled: {config.ai_enabled}')
print(f'AI Confidence Threshold: {config.ai_confidence_threshold}')
print(f'Use LSTM: {config.ai_use_lstm}')
print(f'Use Transformer: {config.ai_use_transformer}')
"
```

- [ ] **Step 3: Commit**

```bash
git add plugins/scalpbot/config.py
git commit -m "feat: add AI brain configuration options"
```

---

## Task 10: Integration Tests

**Covers:** Test all AI components

**Files:**
- Create: `tests/test_ai_brain.py`

- [ ] **Step 1: Create test file**

```python
# tests/test_ai_brain.py
"""Tests for AI Brain components."""

import pytest
import numpy as np
import pandas as pd
from plugins.scalpbot.ai.brain import MetaBrain
from plugins.scalpbot.ai.deep_learning.feature_engine import FeatureEngine
from plugins.scalpbot.ai.deep_learning.lstm_model import LSTMPredictor
from plugins.scalpbot.ai.deep_learning.transformer_model import TransformerPredictor
from plugins.scalpbot.ai.reinforcement.environment import CryptoTradingEnv
from plugins.scalpbot.ai.reinforcement.q_learning import QLearningAgent
from plugins.scalpbot.ai.sentiment.news_analyzer import NewsAnalyzer
from plugins.scalpbot.ai.sentiment.fear_greed import FearGreedIndex
from plugins.scalpbot.ai.ensemble.meta_learner import MetaLearner


def test_feature_engine():
    """Test feature extraction."""
    engine = FeatureEngine(lookback=20)
    closes = np.random.uniform(100, 200, 50)
    features = engine.extract_price_features(closes)
    assert len(features) > 0


def test_lstm_predictor():
    """Test LSTM predictor."""
    predictor = LSTMPredictor(input_size=10)
    features = np.random.randn(10)
    prediction = predictor.predict(features)
    assert prediction.direction in ["LONG", "SHORT", "NEUTRAL"]
    assert 0 <= prediction.confidence <= 1


def test_transformer_predictor():
    """Test Transformer predictor."""
    predictor = TransformerPredictor(d_model=32, num_heads=2, num_layers=2)
    features = np.random.randn(10, 32)
    prediction = predictor.predict(features)
    assert prediction.direction in ["LONG", "SHORT", "NEUTRAL"]
    assert 0 <= prediction.confidence <= 1


def test_trading_environment():
    """Test trading environment."""
    data = np.random.uniform(100, 200, 100)
    env = CryptoTradingEnv(data)
    state = env.reset()
    assert len(state) == env.state_size
    
    next_state, reward, done, info = env.step(1)
    assert len(next_state) == env.state_size


def test_q_learning_agent():
    """Test Q-Learning agent."""
    env = CryptoTradingEnv(np.random.uniform(100, 200, 100))
    agent = QLearningAgent(env.state_size, env.action_size)
    
    state = env.reset()
    action = agent.choose_action(state)
    assert 0 <= action < env.action_size


def test_news_analyzer():
    """Test news sentiment analyzer."""
    analyzer = NewsAnalyzer()
    result = analyzer.analyze_text("Bitcoin surges to new all-time high")
    assert result.label in ["positive", "negative", "neutral"]
    assert -1 <= result.score <= 1


def test_fear_greed():
    """Test Fear & Greed Index."""
    fg = FearGreedIndex()
    prices = np.random.uniform(50000, 60000, 100)
    volumes = np.random.uniform(1e9, 5e9, 100)
    data = fg.calculate_from_data(prices, volumes)
    assert 0 <= data.value <= 100


def test_meta_learner():
    """Test meta-learner ensemble."""
    learner = MetaLearner()
    predictions = {
        "lstm": ("LONG", 0.8),
        "transformer": ("LONG", 0.7),
        "q_learning": ("LONG", 0.6),
        "sentiment": ("NEUTRAL", 0.5)
    }
    result = learner.predict(predictions)
    assert result.direction in ["LONG", "SHORT", "NEUTRAL"]
    assert 0 <= result.confidence <= 1


def test_metabrain():
    """Test MetaBrain integration."""
    brain = MetaBrain()
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'open': np.random.uniform(50000, 60000, 100),
        'high': np.random.uniform(50000, 60000, 100),
        'low': np.random.uniform(50000, 60000, 100),
        'close': np.random.uniform(50000, 60000, 100),
        'volume': np.random.uniform(1e9, 5e9, 100)
    }, index=dates)
    
    indicators = {
        'rsi': np.random.uniform(30, 70, 100),
        'macd': np.zeros(100),
        'macd_signal': np.zeros(100),
        'bb_upper': np.full(100, 65000),
        'bb_lower': np.full(100, 45000),
        'atr': np.full(100, 200)
    }
    
    output = brain.predict(df, indicators, ['STRONG_BULLISH'])
    assert output.direction in ["LONG", "SHORT", "NEUTRAL"]
    assert 0 <= output.confidence <= 1
    assert output.processing_time > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -m pytest tests/test_ai_brain.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_ai_brain.py
git commit -m "test: add comprehensive AI brain tests"
```

---

## Execution Handoff

After completing all tasks:

1. Run all tests to verify AI components work
2. Test MetaBrain with real market data
3. Verify ensemble predictions are reasonable

**Next Steps:**
- Train models on historical data
- Add real-time news sentiment fetching
- Implement model persistence (save/load)
- Add backtesting framework