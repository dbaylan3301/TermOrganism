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
        
        import torch.nn as nn
        
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    dropout=dropout,
                    batch_first=True
                )
                self.fc = nn.Sequential(
                    nn.Linear(hidden_size, 64),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(64, 32),
                    nn.ReLU(),
                    nn.Linear(32, 3)  # [LONG, SHORT, NEUTRAL]
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
