"""Web Dashboard - Streamlit Interface."""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

# Page config
st.set_page_config(
    page_title="TermOrganism Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .positive { color: #00ff00; }
    .negative { color: #ff0000; }
    .neutral { color: #ffff00; }
</style>
""", unsafe_allow_html=True)

class TradingDashboard:
    """Streamlit trading dashboard."""
    
    def __init__(self):
        self.data = {}
        self.signals = []
        self.trades = []
    
    def run(self):
        """Dashboard'ı çalıştır."""
        st.title("📈 TermOrganism Trading Dashboard")
        
        # Sidebar
        self._render_sidebar()
        
        # Main content
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self._render_metric_card("Portfolio Value", "$10,234", "+2.3%")
        with col2:
            self._render_metric_card("Daily PnL", "+$156", "+1.5%")
        with col3:
            self._render_metric_card("Win Rate", "68%", "")
        with col4:
            self._render_metric_card("Sharpe Ratio", "1.85", "")
        
        st.divider()
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Equity Curve", 
            "🎯 Signals", 
            "📈 Positions",
            "🧠 AI Analysis",
            "📋 Trades"
        ])
        
        with tab1:
            self._render_equity_curve()
        
        with tab2:
            self._render_signals()
        
        with tab3:
            self._render_positions()
        
        with tab4:
            self._render_ai_analysis()
        
        with tab5:
            self._render_trades()
    
    def _render_sidebar(self):
        """Sidebar."""
        with st.sidebar:
            st.header("⚙️ Settings")
            
            # Exchange selection
            exchange = st.selectbox("Exchange", ["MEXC", "Binance", "Bybit"])
            
            # Symbols
            symbols = st.multiselect(
                "Symbols",
                ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA"],
                default=["BTC", "ETH"]
            )
            
            # Timeframe
            timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])
            
            # Strategy
            strategy = st.selectbox("Strategy", ["Ensemble", "ML Only", "LSTM", "Sentiment"])
            
            st.divider()
            
            # Risk settings
            st.subheader("Risk Management")
            stop_loss = st.slider("Stop Loss %", 0.5, 5.0, 2.0)
            take_profit = st.slider("Take Profit %", 1.0, 10.0, 4.0)
            position_size = st.slider("Position Size %", 1.0, 20.0, 10.0)
            
            st.divider()
            
            # Actions
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
            
            if st.button("▶️ Start Trading", use_container_width=True):
                st.success("Trading started!")
    
    def _render_metric_card(self, title: str, value: str, change: str):
        """Metric card."""
        st.metric(label=title, value=value, delta=change)
    
    def _render_equity_curve(self):
        """Equity curve grafiği."""
        st.subheader("Equity Curve")
        
        # Sample data
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        equity = 10000 + np.cumsum(np.random.randn(30) * 100)
        
        df = pd.DataFrame({
            'Date': dates,
            'Equity': equity
        })
        
        st.line_chart(df.set_index('Date')['Equity'])
        
        # Monthly returns
        st.subheader("Monthly Returns")
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        returns = [2.3, -1.2, 4.5, 1.8, -0.5, 3.2]
        
        st.bar_chart(pd.DataFrame({
            'Month': months,
            'Return %': returns
        }).set_index('Month'))
    
    def _render_signals(self):
        """Sinyaller."""
        st.subheader("Recent Signals")
        
        # Sample signals
        signals = [
            {"time": "14:32", "symbol": "BTC", "direction": "LONG", "confidence": 78, "price": 67500},
            {"time": "14:28", "symbol": "ETH", "direction": "SHORT", "confidence": 65, "price": 3450},
            {"time": "14:15", "symbol": "SOL", "direction": "LONG", "confidence": 82, "price": 145},
            {"time": "14:02", "symbol": "BTC", "direction": "NEUTRAL", "confidence": 45, "price": 67400},
        ]
        
        for signal in signals:
            color = "🟢" if signal['direction'] == "LONG" else "🔴" if signal['direction'] == "SHORT" else "🟡"
            
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
            
            with col1:
                st.write(f"**{signal['time']}**")
            with col2:
                st.write(f"**{signal['symbol']}**")
            with col3:
                st.write(f"{color} {signal['direction']}")
            with col4:
                st.write(f"{signal['confidence']}%")
            with col5:
                st.write(f"${signal['price']:,.2f}")
    
    def _render_positions(self):
        """Açık pozisyonlar."""
        st.subheader("Open Positions")
        
        # Sample positions
        positions = [
            {"symbol": "BTC", "side": "LONG", "entry": 66500, "current": 67500, "size": 0.15, "pnl": 150},
            {"symbol": "ETH", "side": "LONG", "entry": 3400, "current": 3450, "size": 2.5, "pnl": 125},
        ]
        
        for pos in positions:
            pnl_color = "positive" if pos['pnl'] > 0 else "negative"
            
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    st.write(f"**{pos['symbol']}**")
                with col2:
                    st.write(f"{pos['side']}")
                with col3:
                    st.write(f"${pos['entry']:,.2f}")
                with col4:
                    st.write(f"${pos['current']:,.2f}")
                with col5:
                    st.write(f"{pos['size']}")
                with col6:
                    st.markdown(f'<span class="{pnl_color}">+${pos["pnl"]}</span>', unsafe_allow_html=True)
    
    def _render_ai_analysis(self):
        """AI analiz."""
        st.subheader("AI Analysis")
        
        # Model status
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**ML Ensemble Status**")
            st.write("- XGBoost: ✅ Trained")
            st.write("- LightGBM: ✅ Trained")
            st.write("- LSTM: ✅ Trained")
            st.write("- Accuracy: 68.5%")
        
        with col2:
            st.write("**Sentiment Analysis**")
            st.write("- News: Positive (0.42)")
            st.write("- Social: Neutral (0.15)")
            st.write("- Fear & Greed: 55 (Neutral)")
            st.write("- Overall: Positive (0.32)")
        
        st.divider()
        
        # Feature importance
        st.write("**Top Features**")
        features = {
            'RSI': 0.15,
            'MACD': 0.12,
            'Volume Ratio': 0.11,
            'EMA Cross': 0.10,
            'ATR': 0.09
        }
        
        st.bar_chart(pd.DataFrame({
            'Feature': list(features.keys()),
            'Importance': list(features.values())
        }).set_index('Feature'))
        
        # LSTM prediction
        st.divider()
        st.write("**LSTM Prediction**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("LONG", "62%", "+5%")
        with col2:
            st.metric("SHORT", "28%", "-3%")
        with col3:
            st.metric("NEUTRAL", "10%", "-2%")
    
    def _render_trades(self):
        """İşlem geçmişi."""
        st.subheader("Trade History")
        
        # Sample trades
        trades = [
            {"time": "14:30", "symbol": "BTC", "side": "LONG", "entry": 66500, "exit": 67500, "pnl": 150, "duration": "2h"},
            {"time": "12:15", "symbol": "ETH", "side": "SHORT", "entry": 3500, "exit": 3450, "pnl": 125, "duration": "1.5h"},
            {"time": "10:00", "symbol": "SOL", "side": "LONG", "entry": 140, "exit": 145, "pnl": 75, "duration": "3h"},
        ]
        
        # Table
        df = pd.DataFrame(trades)
        st.dataframe(df, use_container_width=True)
        
        # Stats
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Trades", "45")
        with col2:
            st.metric("Win Rate", "68%")
        with col3:
            st.metric("Total PnL", "+$2,345")

def main():
    """Ana fonksiyon."""
    dashboard = TradingDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
