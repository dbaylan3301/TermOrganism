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
