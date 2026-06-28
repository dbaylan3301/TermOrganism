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
        print("Initializing MetaBrain...")
        
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
        
        print("MetaBrain initialized")
    
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
        print("RL agents initialized")
    
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
        print("Training MetaBrain...")
        
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
        
        print("MetaBrain training complete")
    
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
