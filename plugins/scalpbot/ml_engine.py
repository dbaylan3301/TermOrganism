"""ML Ensemble - XGBoost + LightGBM."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class MLPrediction:
    direction: str = "NEUTRAL"  # LONG, SHORT, NEUTRAL
    confidence: float = 0.0
    probability_long: float = 0.0
    probability_short: float = 0.0
    feature_importance: Dict[str, float] = None
    
    def __post_init__(self):
        if self.feature_importance is None:
            self.feature_importance = {}

class MLEnsemble:
    """XGBoost + LightGBM ensemble."""
    
    def __init__(self):
        self.xgb_model = None
        self.lgb_model = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        
        # Import
        try:
            import xgboost as xgb
            import lightgbm as lgb
            from sklearn.preprocessing import RobustScaler
            self.xgb = xgb
            self.lgb = lgb
            self.RobustScaler = RobustScaler
            self.available = True
        except ImportError:
            self.available = False
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ham veriden feature üret."""
        features = pd.DataFrame(index=df.index)
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values
        
        # Güvenli bölme için
        with np.errstate(divide='ignore', invalid='ignore'):
            # Price features
            features['returns_1'] = df['close'].pct_change(1)
            features['returns_5'] = df['close'].pct_change(5)
            features['returns_10'] = df['close'].pct_change(10)
            features['returns_20'] = df['close'].pct_change(20)
            
            # Volatility features
            features['volatility_10'] = df['close'].pct_change().rolling(10).std()
            features['volatility_20'] = df['close'].pct_change().rolling(20).std()
            vol20 = features['volatility_20'].replace(0, np.nan)
            features['volatility_ratio'] = features['volatility_10'] / vol20
            
            # Volume features
            vol_ma = df['volume'].rolling(20).mean().replace(0, np.nan)
            features['volume_ma_ratio'] = df['volume'] / vol_ma
            features['volume_change'] = df['volume'].pct_change()
            
            # Price range features
            hl_range = (df['high'] - df['low']).replace(0, np.nan)
            features['high_low_ratio'] = (df['high'] - df['low']) / df['close']
            features['close_position'] = (df['close'] - df['low']) / hl_range
            
            # Trend features
            features['ema_9'] = df['close'].ewm(span=9).mean()
            features['ema_21'] = df['close'].ewm(span=21).mean()
            features['ema_50'] = df['close'].ewm(span=50).mean()
            ema21 = features['ema_21'].replace(0, np.nan)
            ema50 = features['ema_50'].replace(0, np.nan)
            features['ema_ratio_9_21'] = features['ema_9'] / ema21
            features['ema_ratio_21_50'] = features['ema_21'] / ema50
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            loss_safe = loss.replace(0, np.nan)
            rs = gain / loss_safe
            features['rsi'] = 100 - (100 / (1 + rs))
            features['rsi_ma'] = features['rsi'].rolling(5).mean()
            
            # MACD
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            features['macd'] = ema12 - ema26
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_hist'] = features['macd'] - features['macd_signal']
            
            # ATR
            tr = pd.DataFrame({
                'hl': df['high'] - df['low'],
                'hc': abs(df['high'] - df['close'].shift()),
                'lc': abs(df['low'] - df['close'].shift())
            }).max(axis=1)
            features['atr'] = tr.rolling(14).mean()
            atr_ma = features['atr'].rolling(20).mean().replace(0, np.nan)
            features['atr_ratio'] = features['atr'] / atr_ma
            
            # ADX (basit)
            plus_dm = df['high'].diff()
            minus_dm = -df['low'].diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            
            atr14 = tr.rolling(14).mean()
            atr14_safe = atr14.replace(0, np.nan)
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr14_safe)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr14_safe)
            di_sum = (plus_di + minus_di).replace(0, np.nan)
            dx = 100 * abs(plus_di - minus_di) / di_sum
            features['adx'] = dx.rolling(14).mean()
            
            # Momentum
            shift5 = df['close'].shift(5).replace(0, np.nan)
            shift10 = df['close'].shift(10).replace(0, np.nan)
            shift20 = df['close'].shift(20).replace(0, np.nan)
            features['momentum_5'] = df['close'] / shift5 - 1
            features['momentum_10'] = df['close'] / shift10 - 1
            features['momentum_20'] = df['close'] / shift20 - 1
            
            # Candle features
            features['body_ratio'] = abs(df['close'] - df['open']) / hl_range
            features['is_bullish'] = (df['close'] > df['open']).astype(int)
            features['bullish_ratio'] = features['is_bullish'].rolling(10).mean()
            
            # Support/Resistance
            high_20 = df['high'].rolling(20).max()
            low_20 = df['low'].rolling(20).min()
            features['dist_from_high_20'] = (high_20 - df['close']) / df['close']
            features['dist_from_low_20'] = (df['close'] - low_20) / df['close']
        
        # NaN ve infinity temizle
        features = features.replace([np.inf, -np.inf], np.nan)
        
        self.feature_names = features.columns.tolist()
        
        return features
    
    def create_labels(self, df: pd.DataFrame, forward_period: int = 10, threshold: float = 0.005) -> np.ndarray:
        """Gelecek fiyat hareketine göre etiket oluştur (Binary: 0=SHORT/NEUTRAL, 1=LONG)."""
        future_returns = df['close'].shift(-forward_period) / df['close'] - 1
        
        labels = np.zeros(len(df))
        labels[future_returns > threshold] = 1   # LONG
        labels[future_returns < -threshold] = 0  # SHORT/NEUTRAL
        
        return labels
    
    def train(self, df: pd.DataFrame, forward_period: int = 10, threshold: float = 0.005) -> Dict:
        """ML modellerini eğit."""
        if not self.available:
            return {"status": "error", "message": "ML kütüphaneleri yüklü değil"}
        
        # Features hazırla
        features = self.prepare_features(df)
        labels = self.create_labels(df, forward_period, threshold)
        
        # NaN ve Infinity temizle
        features = features.replace([np.inf, -np.inf], np.nan)
        valid_mask = ~features.isna().any(axis=1) & ~np.isnan(labels)
        features = features[valid_mask]
        labels = labels[valid_mask]
        
        # Son bir temizlik - herhangi bir NaN kalmışsa
        features = features.fillna(0)
        
        if len(features) < 100:
            return {"status": "error", "message": f"Yetersiz veri: {len(features)}"}
        
        # Train/test split (son %20 test)
        split_idx = int(len(features) * 0.8)
        X_train = features.iloc[:split_idx]
        X_test = features.iloc[split_idx:]
        y_train = labels[:split_idx]
        y_test = labels[split_idx:]
        
        # Scaling
        self.scaler = self.RobustScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # XGBoost
        self.xgb_model = self.xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective='binary:logistic',
            eval_metric='logloss',
            verbosity=0
        )
        self.xgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)
        
        # LightGBM
        self.lgb_model = self.lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective='binary',
            verbose=-1
        )
        self.lgb_model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)])
        
        # Evaluate
        xgb_pred = self.xgb_model.predict(X_test_scaled)
        lgb_pred = self.lgb_model.predict(X_test_scaled)
        
        # Ensemble prediction
        ensemble_pred = (xgb_pred + lgb_pred) / 2
        ensemble_pred = np.round(ensemble_pred).astype(int)
        
        # Accuracy
        xgb_acc = np.mean(xgb_pred == y_test) * 100
        lgb_acc = np.mean(lgb_pred == y_test) * 100
        ensemble_acc = np.mean(ensemble_pred == y_test) * 100
        
        # Feature importance
        feature_importance = {}
        xgb_imp = self.xgb_model.feature_importances_
        lgb_imp = self.lgb_model.feature_importances_
        avg_imp = (xgb_imp + lgb_imp) / 2
        
        for i, name in enumerate(self.feature_names):
            feature_importance[name] = float(avg_imp[i])
        
        self.is_trained = True
        
        return {
            "status": "success",
            "xgb_accuracy": round(xgb_acc, 2),
            "lgb_accuracy": round(lgb_acc, 2),
            "ensemble_accuracy": round(ensemble_acc, 2),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "top_features": sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def predict(self, df: pd.DataFrame) -> MLPrediction:
        """Tahmin yap."""
        if not self.available or not self.is_trained:
            return MLPrediction(direction="NEUTRAL", confidence=0)
        
        # Features hazırla
        features = self.prepare_features(df)
        
        # Son satırı al
        last_features = features.iloc[[-1]]
        
        # NaN ve infinity temizle
        last_features = last_features.replace([np.inf, -np.inf], np.nan)
        last_features = last_features.fillna(0)
        
        # Scaling
        X_scaled = self.scaler.transform(last_features)
        
        # Prediction
        xgb_pred = self.xgb_model.predict_proba(X_scaled)[0]
        lgb_pred = self.lgb_model.predict_proba(X_scaled)[0]
        
        # Ensemble
        ensemble_proba = (xgb_pred + lgb_pred) / 2
        
        # Binary: 0=SHORT/NEUTRAL, 1=LONG
        prob_long = float(ensemble_proba[1]) if len(ensemble_proba) > 1 else 0
        prob_short = float(ensemble_proba[0]) if len(ensemble_proba) > 0 else 0
        
        # Direction belirle
        confidence = max(prob_long, prob_short) * 100
        
        if prob_long > 0.6:
            direction = "LONG"
        elif prob_short > 0.6:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
        
        # Feature importance
        feature_importance = {}
        if self.xgb_model is not None:
            xgb_imp = self.xgb_model.feature_importances_
            for i, name in enumerate(self.feature_names):
                if i < len(xgb_imp):
                    feature_importance[name] = float(xgb_imp[i])
        
        return MLPrediction(
            direction=direction,
            confidence=confidence,
            probability_long=prob_long * 100,
            probability_short=prob_short * 100,
            feature_importance=dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5])
        )
    
    def save(self, path: str = "ml_model.pkl") -> bool:
        """Modeli kaydet."""
        if not self.is_trained:
            return False
        
        try:
            import pickle
            data = {
                'xgb_model': self.xgb_model,
                'lgb_model': self.lgb_model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception:
            return False
    
    def load(self, path: str = "ml_model.pkl") -> bool:
        """Modeli yükle."""
        try:
            import pickle
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.xgb_model = data['xgb_model']
            self.lgb_model = data['lgb_model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
            self.is_trained = True
            return True
        except Exception:
            return False
