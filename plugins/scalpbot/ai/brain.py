"""MetaBrain - orchestrates all AI brains."""

import numpy as np
import torch
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
from .neural.scalp_brain import ScalpBrain
from .hybrid.neuro_symbolic import NeuroSymbolicTrader
from .symbolic.rule_engine import SymbolicRuleEngine
from .symbolic.fuzzy_logic import FuzzyTradingSystem
from .forge.ai_forge import AIForge
from .forge.monitor import BrainMonitor
from .forge.logger import DecisionLogger


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
        
        # Neuro-Symbolic
        self.hybrid_model = NeuroSymbolicTrader(input_dim=32, hidden_dim=128)
        self.symbolic_engine = SymbolicRuleEngine()
        self.fuzzy_system = FuzzyTradingSystem()
        
        # AI Forge
        self.forge = AIForge()
        self.monitor = BrainMonitor()
        self.logger = DecisionLogger()
        
        # State
        self.is_initialized = False
        self.prediction_count = 0
        
        self.forge.log("🚀 MetaBrain with Neuro-Symbolic AI initialized")
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
        Make prediction using all brains including Neuro-Symbolic hybrid.
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
        
        # 6. Neuro-Symbolic Hybrid Decision
        hybrid_decision = None
        try:
            hybrid_input = torch.FloatTensor(features.price_features[:32]).unsqueeze(0).unsqueeze(0)
            # Ensure indicators are scalar values for rule engine
            clean_indicators = {}
            for k, v in indicators.items():
                if isinstance(v, (list, np.ndarray)):
                    clean_indicators[k] = float(v[-1]) if len(v) > 0 else 0.0
                else:
                    clean_indicators[k] = v
            hybrid_decision = self.hybrid_model.make_decision(hybrid_input, clean_indicators)
            
            self.monitor.record_decision({
                "action": hybrid_decision.action,
                "confidence": hybrid_decision.confidence,
                "risk_level": hybrid_decision.risk_level
            })
            
            self.logger.log_signal(
                symbol=str(df.index[-1]) if hasattr(df.index, '__getitem__') else "unknown",
                action=hybrid_decision.action,
                confidence=hybrid_decision.confidence,
                indicators=clean_indicators,
                neural_output={"lstm": lstm_output, "transformer": transformer_output},
                symbolic_output={"rules_triggered": len(hybrid_decision.explanation.split('\n'))}
            )
        except Exception as e:
            self.forge.log(f"⚠️ Hybrid model error: {e}", "WARNING")
        
        processing_time = time.time() - start_time
        self.prediction_count += 1
        
        # Use hybrid decision as final direction if available
        final_direction = hybrid_decision.action if hybrid_decision else meta_prediction.direction
        final_confidence = hybrid_decision.confidence if hybrid_decision else meta_prediction.confidence
        
        return BrainOutput(
            direction=final_direction,
            confidence=final_confidence,
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
                "sentiment": "active",
                "neuro_symbolic": "active",
                "symbolic_engine": "active",
                "fuzzy_system": "active",
                "forge": "active"
            },
            "monitor": self.monitor.get_summary() if self.monitor else None
        }
