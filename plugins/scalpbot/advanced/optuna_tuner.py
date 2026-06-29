"""Optuna Hyperparameter Tuning - Walk-Forward Optimization."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TuningResult:
    best_params: Dict
    best_score: float
    all_trials: List[Dict]
    feature_importance: Dict[str, float]
    optimization_history: List[float]

class OptunaTuner:
    """Optuna ile hyperparameter tuning."""
    
    def __init__(self, objective: str = "sharpe"):
        self.objective = objective
        self.study = None
        self.best_params = None
        self.cache = {}
        
        try:
            import optuna
            self.optuna = optuna
            self.available = True
        except ImportError:
            self.available = False
    
    def create_objective_function(self, df: pd.DataFrame, model_class, 
                                   forward_period: int = 10, 
                                   threshold: float = 0.005) -> Callable:
        """Objective function oluştur."""
        
        def objective(trial):
            # Cache key
            params_key = str(trial.params)
            if params_key in self.cache:
                return self.cache[params_key]
            
            # Hyperparameter suggestions
            params = {
                "learning_rate": trial.suggest_float("lr", 0.01, 0.3, log=True),
                "max_depth": trial.suggest_int("depth", 3, 12),
                "n_estimators": trial.suggest_int("n_est", 50, 800),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child", 1, 10),
                "reg_alpha": trial.suggest_float("alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("lambda", 1e-8, 10.0, log=True),
            }
            
            # Walk-forward backtest
            score = self._walk_forward_backtest(
                df, params, model_class, forward_period, threshold
            )
            
            # Cache'le
            self.cache[params_key] = score
            
            return score
        
        return objective
    
    def _walk_forward_backtest(self, df: pd.DataFrame, params: Dict, 
                                model_class, forward_period: int, 
                                threshold: float) -> float:
        """Walk-forward optimization ile backtest."""
        try:
            import xgboost as xgb
            import lightgbm as lgb
            from sklearn.preprocessing import RobustScaler
        except ImportError:
            return 0.0
        
        # Feature preparation
        features = self._prepare_features(df)
        labels = self._create_labels(df, forward_period, threshold)
        
        # NaN cleanup
        features = features.replace([np.inf, -np.inf], np.nan)
        valid_mask = ~features.isna().any(axis=1) & ~np.isnan(labels)
        features = features[valid_mask]
        labels = labels[valid_mask]
        features = features.fillna(0)
        
        if len(features) < 200:
            return 0.0
        
        # Walk-forward split
        n_splits = 5
        split_size = len(features) // (n_splits + 1)
        
        scores = []
        
        for i in range(n_splits):
            train_end = split_size * (i + 2)
            test_end = min(train_end + split_size, len(features))
            
            if test_end <= train_end:
                continue
            
            X_train = features.iloc[:train_end]
            X_test = features.iloc[train_end:test_end]
            y_train = labels[:train_end]
            y_test = labels[train_end:test_end]
            
            # Scaling
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Model with params
            if model_class == "xgb":
                model = xgb.XGBClassifier(
                    learning_rate=params["learning_rate"],
                    max_depth=params["max_depth"],
                    n_estimators=params["n_estimators"],
                    subsample=params["subsample"],
                    colsample_bytree=params["colsample_bytree"],
                    min_child_weight=params["min_child_weight"],
                    reg_alpha=params["reg_alpha"],
                    reg_lambda=params["reg_lambda"],
                    random_state=42,
                    objective='binary:logistic',
                    eval_metric='logloss',
                    verbosity=0
                )
            else:
                model = lgb.LGBMClassifier(
                    learning_rate=params["learning_rate"],
                    max_depth=params["max_depth"],
                    n_estimators=params["n_estimators"],
                    subsample=params["subsample"],
                    colsample_bytree=params["colsample_bytree"],
                    min_child_weight=params["min_child_weight"],
                    reg_alpha=params["reg_alpha"],
                    reg_lambda=params["reg_lambda"],
                    random_state=42,
                    objective='binary',
                    verbose=-1
                )
            
            model.fit(X_train_scaled, y_train)
            
            # Predict & Score
            pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            
            # Custom scoring
            score = self._calculate_score(y_test, pred_proba)
            scores.append(score)
        
        return np.mean(scores) if scores else 0.0
    
    def _calculate_score(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        """Özel skor hesapla (Sharpe + Profit Factor + Max DD penalty)."""
        from sklearn.metrics import accuracy_score
        
        # Binary predictions
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        # Accuracy
        accuracy = accuracy_score(y_true, y_pred)
        
        # Simulate returns
        returns = np.where(y_pred == 1, y_pred_proba - 0.5, 0.5 - y_pred_proba)
        
        # Sharpe Ratio (annualized)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        # Profit Factor
        gross_profit = np.sum(returns[returns > 0])
        gross_loss = abs(np.sum(returns[returns < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 1.0
        
        # Max Drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0
        
        # Combined score
        score = (
            0.4 * accuracy +
            0.3 * min(sharpe, 3.0) / 3.0 +  # Cap sharpe at 3
            0.2 * min(profit_factor, 5.0) / 5.0 +  # Cap PF at 5
            0.1 * (1 - min(max_drawdown, 0.5) / 0.5)  # Penalize drawdown
        )
        
        return score
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature preparation (same as ml_engine)."""
        features = pd.DataFrame(index=df.index)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            features['returns_1'] = df['close'].pct_change(1)
            features['returns_5'] = df['close'].pct_change(5)
            features['returns_10'] = df['close'].pct_change(10)
            features['returns_20'] = df['close'].pct_change(20)
            
            features['volatility_10'] = df['close'].pct_change().rolling(10).std()
            features['volatility_20'] = df['close'].pct_change().rolling(20).std()
            vol20 = features['volatility_20'].replace(0, np.nan)
            features['volatility_ratio'] = features['volatility_10'] / vol20
            
            vol_ma = df['volume'].rolling(20).mean().replace(0, np.nan)
            features['volume_ma_ratio'] = df['volume'] / vol_ma
            features['volume_change'] = df['volume'].pct_change()
            
            features['high_low_ratio'] = (df['high'] - df['low']) / df['close']
            hl_range = (df['high'] - df['low']).replace(0, np.nan)
            features['close_position'] = (df['close'] - df['low']) / hl_range
            
            features['ema_9'] = df['close'].ewm(span=9).mean()
            features['ema_21'] = df['close'].ewm(span=21).mean()
            features['ema_50'] = df['close'].ewm(span=50).mean()
            ema21 = features['ema_21'].replace(0, np.nan)
            ema50 = features['ema_50'].replace(0, np.nan)
            features['ema_ratio_9_21'] = features['ema_9'] / ema21
            features['ema_ratio_21_50'] = features['ema_21'] / ema50
            
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            loss_safe = loss.replace(0, np.nan)
            rs = gain / loss_safe
            features['rsi'] = 100 - (100 / (1 + rs))
            
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            features['macd'] = ema12 - ema26
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_hist'] = features['macd'] - features['macd_signal']
        
        features = features.replace([np.inf, -np.inf], np.nan)
        return features
    
    def _create_labels(self, df: pd.DataFrame, forward_period: int, 
                        threshold: float) -> np.ndarray:
        """Label creation."""
        future_returns = df['close'].shift(-forward_period) / df['close'] - 1
        labels = np.zeros(len(df))
        labels[future_returns > threshold] = 1
        return labels
    
    def tune(self, df: pd.DataFrame, model_class: str = "xgb", 
             n_trials: int = 50, forward_period: int = 10, 
             threshold: float = 0.005) -> TuningResult:
        """Optuna tuning çalıştır."""
        if not self.available:
            return TuningResult({}, 0.0, [], {}, [])
        
        # Study oluştur
        self.study = self.optuna.create_study(
            direction="maximize",
            sampler=self.optuna.samplers.TPESampler(seed=42)
        )
        
        # Objective function
        objective_fn = self.create_objective_function(
            df, model_class, forward_period, threshold
        )
        
        # Optimize
        self.study.optimize(objective_fn, n_trials=n_trials, show_progress_bar=False)
        
        # Results
        best_params = self.study.best_params
        best_score = self.study.best_value
        
        all_trials = []
        for trial in self.study.trials:
            all_trials.append({
                'number': trial.number,
                'value': trial.value,
                'params': trial.params,
                'state': str(trial.state)
            })
        
        # Feature importance (from best model)
        feature_importance = self._get_feature_importance(df, best_params, model_class)
        
        # Optimization history
        optimization_history = [t['value'] for t in all_trials if t['value'] is not None]
        
        self.best_params = best_params
        
        return TuningResult(
            best_params=best_params,
            best_score=best_score,
            all_trials=all_trials,
            feature_importance=feature_importance,
            optimization_history=optimization_history
        )
    
    def _get_feature_importance(self, df: pd.DataFrame, params: Dict, 
                                 model_class: str) -> Dict[str, float]:
        """Best model'den feature importance al."""
        try:
            import xgboost as xgb
            import lightgbm as lgb
            from sklearn.preprocessing import RobustScaler
        except ImportError:
            return {}
        
        features = self._prepare_features(df)
        labels = self._create_labels(df, 10, 0.005)
        
        features = features.replace([np.inf, -np.inf], np.nan)
        valid_mask = ~features.isna().any(axis=1) & ~np.isnan(labels)
        features = features[valid_mask]
        labels = labels[valid_mask]
        features = features.fillna(0)
        
        if len(features) < 100:
            return {}
        
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(features)
        
        if model_class == "xgb":
            model = xgb.XGBClassifier(
                learning_rate=params.get("lr", 0.1),
                max_depth=params.get("depth", 6),
                n_estimators=params.get("n_est", 200),
                subsample=params.get("subsample", 0.8),
                colsample_bytree=params.get("colsample", 0.8),
                random_state=42,
                verbosity=0
            )
        else:
            model = lgb.LGBMClassifier(
                learning_rate=params.get("lr", 0.1),
                max_depth=params.get("depth", 6),
                n_estimators=params.get("n_est", 200),
                subsample=params.get("subsample", 0.8),
                colsample_bytree=params.get("colsample", 0.8),
                random_state=42,
                verbose=-1
            )
        
        model.fit(X_scaled, labels)
        
        importance = {}
        imp_values = model.feature_importances_
        for i, col in enumerate(features.columns):
            if i < len(imp_values):
                importance[col] = float(imp_values[i])
        
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])
    
    def get_best_params(self) -> Dict:
        """En iyi parametreleri döndür."""
        return self.best_params or {}
    
    def save_results(self, path: str = "optuna_results.json") -> bool:
        """Sonuçları kaydet."""
        if not self.study:
            return False
        
        try:
            import json
            data = {
                'best_params': self.study.best_params,
                'best_value': self.study.best_value,
                'n_trials': len(self.study.trials)
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
