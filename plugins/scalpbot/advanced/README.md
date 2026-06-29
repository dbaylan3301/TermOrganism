# Advanced Trading Features

## Overview

This module contains advanced trading features for the TermOrganism scalpbot:

1. **Optuna Hyperparameter Tuning** - Walk-forward optimization for ML models
2. **WebSocket Real-time Data** - Live market data streaming
3. **Backtest Engine** - Professional backtesting with Monte Carlo simulation
4. **LSTM Sequence Model** - Deep learning for time series prediction
5. **Enhanced Sentiment** - LLM-powered news and social sentiment analysis
6. **Web Dashboard** - Streamlit-based monitoring interface

## Quick Start

### 1. Optuna Tuning

```python
from plugins.scalpbot.advanced import OptunaTuner
import pandas as pd

# Load your data
df = pd.read_csv("market_data.csv")

# Create tuner
tuner = OptunaTuner(objective="sharpe")

# Run optimization (50 trials)
result = tuner.tune(df, model_class="xgb", n_trials=50)

print(f"Best score: {result.best_score}")
print(f"Best params: {result.best_params}")
```

### 2. WebSocket Stream

```python
from plugins.scalpbot.advanced import WebSocketStream, StreamConfig
import asyncio

async def main():
    stream = WebSocketStream(exchange_id="mexc")
    
    config = StreamConfig(
        symbols=["BTC", "ETH"],
        timeframe="1m",
        buffer_size=1000
    )
    
    # Add callback for new data
    async def on_data(data_point):
        print(f"New price: {data_point['symbol']} @ {data_point['last']}")
    
    stream.add_callback(on_data)
    
    # Start streaming
    await stream.start(config)
    
    # Keep running
    await asyncio.sleep(3600)
    await stream.stop()

asyncio.run(main())
```

### 3. Backtesting

```python
from plugins.scalpbot.advanced import BacktestEngine, BacktestConfig

# Configure
config = BacktestConfig(
    initial_capital=10000,
    position_size=0.1,
    stop_loss=0.02,
    take_profit=0.04
)

# Create engine
engine = BacktestEngine(config)

# Define your signal function
def my_signal(df):
    # Your signal logic here
    return {"direction": "LONG", "confidence": 75}

# Run backtest
result = engine.run(df, my_signal, symbol="BTCUSDT")

print(f"Total return: {result.total_return:.2f}%")
print(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
print(f"Win rate: {result.win_rate:.1f}%")

# Monte Carlo simulation
mc = MonteCarloSimulator(n_simulations=1000)
mc_result = mc.simulate(result.trades, 10000)
print(f"Probability of profit: {mc_result['stats']['probability_of_profit']:.1f}%")
```

### 4. LSTM Model

```python
from plugins.scalpbot.advanced import TradingLSTM, LSTMConfig

# Configure
config = LSTMConfig(
    sequence_length=60,
    hidden_size=128,
    num_layers=2,
    epochs=50
)

# Create model
model = TradingLSTM(config)

# Train
result = model.train(df)
print(f"Accuracy: {result['accuracy']:.2f}%")

# Predict
prediction = model.predict(df)
print(f"Direction: {prediction.direction}")
print(f"Confidence: {prediction.confidence:.1f}%")
```

### 5. Sentiment Analysis

```python
from plugins.scalpbot.advanced import EnhancedSentimentAnalyzer, SentimentConfig
import asyncio

# Configure
config = SentimentConfig(
    cache_ttl=900,
    use_llm=True,
    llm_provider="groq"
)

# Create analyzer
analyzer = EnhancedSentimentAnalyzer(config)

# Get sentiment
async def analyze():
    sentiment = await analyzer.get_sentiment("BTC")
    print(f"Overall score: {sentiment['overall_score']}")
    print(f"Label: {sentiment['overall_label']}")
    
    # Get trading signal
    signal = analyzer.get_trading_signal(sentiment)
    print(f"Signal: {signal['direction']} ({signal['confidence']}%)")

asyncio.run(analyze())
```

### 6. Web Dashboard

```bash
# Install streamlit
pip install streamlit

# Run dashboard
streamlit run plugins/scalpbot/advanced/dashboard.py
```

## Integration with Existing ML Engine

The advanced modules integrate with the existing `ml_engine.py`:

```python
from plugins.scalpbot.ml_engine import MLEnsemble
from plugins.scalpbot.advanced import OptunaTuner, BacktestEngine

# 1. Tune hyperparameters
tuner = OptunaTuner()
result = tuner.tune(df, model_class="xgb", n_trials=50)

# 2. Train with best params
ml = MLEnsemble()
ml.train(df)

# 3. Backtest
engine = BacktestEngine()
backtest_result = engine.run(df, ml.predict)
```

## Dependencies

All dependencies are in `requirements.txt`:

- `optuna>=3.4.0` - Hyperparameter optimization
- `torch>=2.0.0` - Deep learning (LSTM)
- `ccxt-pro>=1.0.0` - WebSocket streaming
- `streamlit>=1.30.0` - Web dashboard

## File Structure

```
plugins/scalpbot/advanced/
├── __init__.py           # Module exports
├── optuna_tuner.py       # Hyperparameter tuning
├── websocket_stream.py   # Real-time data streaming
├── backtest.py           # Backtesting engine
├── lstm_model.py         # LSTM sequence model
├── sentiment_enhanced.py # Enhanced sentiment analysis
└── dashboard.py          # Streamlit web dashboard
```
