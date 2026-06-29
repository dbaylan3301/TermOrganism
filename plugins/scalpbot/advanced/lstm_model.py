"""LSTM Sequence Model - Deep Learning for Trading."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class LSTMConfig:
    sequence_length: int = 60
    input_size: int = 32
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.3
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 50

@dataclass
class LSTMPrediction:
    direction: str  # "LONG", "SHORT", "NEUTRAL"
    confidence: float
    probabilities: Dict[str, float]
    sequence_features: List[float]

class TradingLSTM:
    """LSTM tabanlı trading modeli."""
    
    def __init__(self, config: LSTMConfig = None):
        self.config = config or LSTMConfig()
        self.model = None
        self.scaler = None
        self.device = None
        self.is_trained = False
        
        try:
            import torch
            import torch.nn as nn
            from sklearn.preprocessing import RobustScaler
            self.torch = torch
            self.nn = nn
            self.RobustScaler = RobustScaler
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.available = True
        except ImportError:
            self.available = False
    
    def _build_model(self):
        """LSTM modeli oluştur."""
        class LSTMModel(self.nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = self.nn.LSTM(
                    input_size, hidden_size, num_layers, 
                    batch_first=True, dropout=dropout
                )
                self.fc = self.nn.Linear(hidden_size, 3)  # Long, Short, Neutral
            
            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                return self.fc(lstm_out[:, -1, :])
        
        self.model = LSTMModel(
            self.config.input_size,
            self.config.hidden_size,
            self.config.num_layers,
            self.config.dropout
        ).to(self.device)
    
    def prepare_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Sequence'leri hazırla."""
        # Features
        features = self._extract_features(df)
        
        # Labels
        future_returns = df['close'].shift(-10) / df['close'] - 1
        labels = np.zeros(len(df))
        labels[future_returns > 0.005] = 0  # LONG
        labels[future_returns < -0.005] = 1  # SHORT
        labels[(future_returns >= -0.005) & (future_returns <= 0.005)] = 2  # NEUTRAL
        
        # NaN temizle
        valid_mask = ~np.isnan(features).any(axis=1) & ~np.isnan(labels)
        features = features[valid_mask]
        labels = labels[valid_mask]
        
        # Sequence oluştur
        X, y = [], []
        for i in range(self.config.sequence_length, len(features)):
            X.append(features[i-self.config.sequence_length:i])
            y.append(labels[i])
        
        return np.array(X), np.array(y)
    
    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """Feature extraction."""
        features = []
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values
        
        # Price features
        returns_1 = np.diff(closes) / closes[:-1]
        returns_5 = closes[5:] / closes[:-5] - 1
        returns_10 = closes[10:] / closes[:-10] - 1
        
        # Pad
        returns_1 = np.pad(returns_1, (1, 0), 'edge')
        returns_5 = np.pad(returns_5, (5, 0), 'edge')
        returns_10 = np.pad(returns_10, (10, 0), 'edge')
        
        features.append(returns_1)
        features.append(returns_5)
        features.append(returns_10)
        
        # Volatility
        vol_10 = pd.Series(closes).pct_change().rolling(10).std().values
        vol_20 = pd.Series(closes).pct_change().rolling(20).std().values
        features.append(vol_10)
        features.append(vol_20)
        
        # Volume
        vol_ma = pd.Series(volumes).rolling(20).mean().values
        vol_ratio = volumes / np.where(vol_ma > 0, vol_ma, 1)
        features.append(vol_ratio)
        
        # RSI
        delta = np.diff(closes)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        gain_ma = pd.Series(gain).rolling(14).mean().values
        loss_ma = pd.Series(loss).rolling(14).mean().values
        rs = gain_ma / np.where(loss_ma > 0, loss_ma, 1)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.pad(rsi, (1, 0), 'edge')
        features.append(rsi)
        
        # MACD
        ema12 = pd.Series(closes).ewm(span=12).mean().values
        ema26 = pd.Series(closes).ewm(span=26).mean().values
        macd = ema12 - ema26
        macd_signal = pd.Series(macd).ewm(span=9).mean().values
        macd_hist = macd - macd_signal
        features.append(macd)
        features.append(macd_signal)
        features.append(macd_hist)
        
        # ATR
        tr = np.maximum(
            highs - lows,
            np.maximum(
                np.abs(highs - np.roll(closes, 1)),
                np.abs(lows - np.roll(closes, 1))
            )
        )
        tr[0] = highs[0] - lows[0]
        atr = pd.Series(tr).rolling(14).mean().values
        features.append(atr)
        
        # EMA ratios
        ema9 = pd.Series(closes).ewm(span=9).mean().values
        ema21 = pd.Series(closes).ewm(span=21).mean().values
        ema50 = pd.Series(closes).ewm(span=50).mean().values
        ema_ratio_9_21 = ema9 / np.where(ema21 > 0, ema21, 1)
        ema_ratio_21_50 = ema21 / np.where(ema50 > 0, ema50, 1)
        features.append(ema_ratio_9_21)
        features.append(ema_ratio_21_50)
        
        # Candle features
        body_ratio = np.abs(closes - df['open'].values) / np.where(highs - lows > 0, highs - lows, 1)
        is_bullish = (closes > df['open'].values).astype(float)
        features.append(body_ratio)
        features.append(is_bullish)
        
        # Stack features
        features = np.column_stack(features)
        
        # Replace inf/nan
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features
    
    def train(self, df: pd.DataFrame) -> Dict:
        """Modeli eğit."""
        if not self.available:
            return {"status": "error", "message": "PyTorch yüklü değil"}
        
        # Build model
        self._build_model()
        
        # Prepare data
        X, y = self.prepare_sequences(df)
        
        if len(X) < 100:
            return {"status": "error", "message": f"Yetersiz veri: {len(X)}"}
        
        # Scaling
        self.scaler = self.RobustScaler()
        X_reshaped = X.reshape(-1, X.shape[-1])
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X_scaled = X_scaled.reshape(X.shape)
        
        # Train/test split
        split_idx = int(len(X_scaled) * 0.8)
        X_train = X_scaled[:split_idx]
        X_test = X_scaled[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]
        
        # Convert to tensors
        X_train_tensor = self.torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = self.torch.LongTensor(y_train).to(self.device)
        X_test_tensor = self.torch.FloatTensor(X_test).to(self.device)
        y_test_tensor = self.torch.LongTensor(y_test).to(self.device)
        
        # Dataset & DataLoader
        train_dataset = self.torch.utils.data.TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = self.torch.utils.data.DataLoader(
            train_dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        # Optimizer & Loss
        optimizer = self.torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        criterion = self.nn.CrossEntropyLoss()
        
        # Training loop
        self.model.train()
        train_losses = []
        
        for epoch in range(self.config.epochs):
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(train_loader)
            train_losses.append(avg_loss)
        
        # Evaluation
        self.model.eval()
        with self.torch.no_grad():
            test_outputs = self.model(X_test_tensor)
            _, predicted = self.torch.max(test_outputs, 1)
            accuracy = (predicted == y_test_tensor).float().mean().item() * 100
        
        self.is_trained = True
        
        return {
            "status": "success",
            "accuracy": round(accuracy, 2),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "epochs": self.config.epochs,
            "final_loss": round(train_losses[-1], 4) if train_losses else 0
        }
    
    def predict(self, df: pd.DataFrame) -> LSTMPrediction:
        """Tahmin yap."""
        if not self.available or not self.is_trained:
            return LSTMPrediction(
                direction="NEUTRAL",
                confidence=0,
                probabilities={"LONG": 0, "SHORT": 0, "NEUTRAL": 1},
                sequence_features=[]
            )
        
        # Prepare features
        features = self._extract_features(df)
        
        # Son sequence
        if len(features) < self.config.sequence_length:
            return LSTMPrediction(
                direction="NEUTRAL",
                confidence=0,
                probabilities={"LONG": 0, "SHORT": 0, "NEUTRAL": 1},
                sequence_features=[]
            )
        
        sequence = features[-self.config.sequence_length:]
        
        # Scale
        sequence_reshaped = sequence.reshape(-1, sequence.shape[-1])
        sequence_scaled = self.scaler.transform(sequence_reshaped)
        sequence_scaled = sequence_scaled.reshape(1, self.config.sequence_length, -1)
        
        # Predict
        self.model.eval()
        with self.torch.no_grad():
            input_tensor = self.torch.FloatTensor(sequence_scaled).to(self.device)
            output = self.model(input_tensor)
            probs = self.torch.softmax(output, dim=1).cpu().numpy()[0]
        
        # Decode
        labels = ["LONG", "SHORT", "NEUTRAL"]
        pred_idx = np.argmax(probs)
        
        return LSTMPrediction(
            direction=labels[pred_idx],
            confidence=float(probs[pred_idx]) * 100,
            probabilities={
                "LONG": float(probs[0]) * 100,
                "SHORT": float(probs[1]) * 100,
                "NEUTRAL": float(probs[2]) * 100
            },
            sequence_features=sequence[-1].tolist()
        )
    
    def save(self, path: str = "lstm_model.pt") -> bool:
        """Modeli kaydet."""
        if not self.is_trained:
            return False
        
        try:
            import pickle
            data = {
                'model_state': self.model.state_dict(),
                'scaler': self.scaler,
                'config': self.config
            }
            self.torch.save(data, path)
            return True
        except Exception:
            return False
    
    def load(self, path: str = "lstm_model.pt") -> bool:
        """Modeli yükle."""
        try:
            data = self.torch.load(path, map_location=self.device)
            self.config = data['config']
            self.scaler = data['scaler']
            self._build_model()
            self.model.load_state_dict(data['model_state'])
            self.is_trained = True
            return True
        except Exception:
            return False

class LSTMEnsemble:
    """LSTM + XGBoost stacking ensemble."""
    
    def __init__(self):
        self.lstm = TradingLSTM()
        self.xgb_model = None
        self.is_trained = False
    
    def train(self, df: pd.DataFrame) -> Dict:
        """Stacking ensemble eğit."""
        # LSTM train
        lstm_result = self.lstm.train(df)
        
        if lstm_result.get("status") != "success":
            return lstm_result
        
        # Get LSTM predictions as features
        lstm_features = []
        for i in range(60, len(df)):
            try:
                pred = self.lstm.predict(df.iloc[:i+1])
                lstm_features.append([
                    pred.probabilities["LONG"],
                    pred.probabilities["SHORT"],
                    pred.probabilities["NEUTRAL"]
                ])
            except Exception:
                lstm_features.append([33.33, 33.33, 33.33])
        
        lstm_features = np.array(lstm_features)
        
        # XGBoost on LSTM features + original features
        try:
            import xgboost as xgb
            from sklearn.preprocessing import RobustScaler
            
            # Original features
            features = self.lstm._extract_features(df)
            features = features[60:]  # Align with lstm_features
            
            # Combine
            combined = np.hstack([features, lstm_features])
            
            # Labels
            future_returns = df['close'].shift(-10).values[60:] / df['close'].values[60:] - 1
            labels = np.zeros(len(combined))
            labels[future_returns > 0.005] = 1
            
            # Clean
            valid_mask = ~np.isnan(combined).any(axis=1) & ~np.isnan(labels)
            combined = combined[valid_mask]
            labels = labels[valid_mask]
            
            # Train XGBoost
            scaler = RobustScaler()
            X_scaled = scaler.fit_transform(combined)
            
            self.xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                verbosity=0
            )
            self.xgb_model.fit(X_scaled, labels)
            
            self.is_trained = True
            
            return {
                "status": "success",
                "lstm_accuracy": lstm_result.get("accuracy", 0),
                "ensemble_type": "LSTM + XGBoost stacking",
                "train_size": len(combined)
            }
        
        except ImportError:
            return lstm_result
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """Stacking prediction."""
        if not self.is_trained:
            return {"direction": "NEUTRAL", "confidence": 0}
        
        # LSTM prediction
        lstm_pred = self.lstm.predict(df)
        
        # Get features for XGBoost
        features = self.lstm._extract_features(df)
        lstm_features = np.array([
            lstm_pred.probabilities["LONG"],
            lstm_pred.probabilities["SHORT"],
            lstm_pred.probabilities["NEUTRAL"]
        ]).reshape(1, -1)
        
        combined = np.hstack([features[-1:], lstm_features])
        
        # Scale
        from sklearn.preprocessing import RobustScaler
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(combined)
        
        # XGBoost prediction
        xgb_pred = self.xgb_model.predict_proba(X_scaled)[0]
        
        # Final ensemble
        final_prob_long = (lstm_pred.probabilities["LONG"]/100 + xgb_pred[1]) / 2
        final_prob_short = (lstm_pred.probabilities["SHORT"]/100 + xgb_pred[0]) / 2
        
        if final_prob_long > 0.6:
            direction = "LONG"
            confidence = final_prob_long * 100
        elif final_prob_short > 0.6:
            direction = "SHORT"
            confidence = final_prob_short * 100
        else:
            direction = "NEUTRAL"
            confidence = max(final_prob_long, final_prob_short) * 100
        
        return {
            "direction": direction,
            "confidence": confidence,
            "lstm_probs": lstm_pred.probabilities,
            "xgb_probs": {"LONG": xgb_pred[1]*100, "SHORT": xgb_pred[0]*100},
            "ensemble_probs": {"LONG": final_prob_long*100, "SHORT": final_prob_short*100}
        }
