"""Walk-Forward Validation - Strateji validasyonu."""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

@dataclass
class BacktestResult:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0

@dataclass
class ValidationResult:
    is_valid: bool = False
    in_sample: Optional[BacktestResult] = None
    out_of_sample: Optional[BacktestResult] = None
    overfitting_score: float = 0.0
    reason: str = ""

class WalkForwardValidator:
    """Walk-Forward Optimization validasyonu."""
    
    def __init__(self, in_sample_pct: float = 0.70, min_forward_days: int = 90,
                 min_sharpe: float = 1.2, min_profit_factor: float = 1.6):
        self.in_sample_pct = in_sample_pct
        self.min_forward_days = min_forward_days
        self.min_sharpe = min_sharpe
        self.min_profit_factor = min_profit_factor
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Veriyi in-sample ve out-of-sample olarak böl."""
        n = len(df)
        split_idx = int(n * self.in_sample_pct)
        
        in_sample = df.iloc[:split_idx].copy()
        out_of_sample = df.iloc[split_idx:].copy()
        
        return in_sample, out_of_sample
    
    def backtest_strategy(self, df: pd.DataFrame, signal_func, 
                         initial_capital: float = 10000) -> BacktestResult:
        """Basit strateji backtest'i."""
        result = BacktestResult()
        
        if len(df) < 50:
            return result
        
        trades = []
        capital = initial_capital
        peak_capital = initial_capital
        
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        
        for i in range(50, len(df) - 1):
            # Sinyal üret
            window = df.iloc[max(0, i-50):i+1]
            signal = signal_func(window)
            
            if signal in ["LONG", "SHORT"]:
                entry_price = closes[i]
                entry_idx = i
                
                # Basit exit: 10 mum sonra veya %2 stop/target
                exit_idx = min(i + 10, len(df) - 1)
                exit_price = closes[exit_idx]
                
                if signal == "LONG":
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
                
                trades.append({
                    "signal": signal,
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl_pct": pnl_pct,
                })
                
                capital *= (1 + pnl_pct / 100)
                peak_capital = max(peak_capital, capital)
        
        # Sonuçları hesapla
        if trades:
            result.total_trades = len(trades)
            wins = [t for t in trades if t["pnl_pct"] > 0]
            losses = [t for t in trades if t["pnl_pct"] <= 0]
            
            result.winning_trades = len(wins)
            result.losing_trades = len(losses)
            result.win_rate = len(wins) / len(trades) * 100
            
            if wins:
                result.avg_win = np.mean([t["pnl_pct"] for t in wins])
            if losses:
                result.avg_loss = abs(np.mean([t["pnl_pct"] for t in losses]))
            
            # Profit Factor
            gross_profit = sum(t["pnl_pct"] for t in wins)
            gross_loss = abs(sum(t["pnl_pct"] for t in losses))
            result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Sharpe Ratio (basit)
            returns = [t["pnl_pct"] for t in trades]
            if len(returns) > 1:
                result.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            # Max Drawdown
            equity_curve = [initial_capital]
            for t in trades:
                equity_curve.append(equity_curve[-1] * (1 + t["pnl_pct"] / 100))
            
            peak = equity_curve[0]
            max_dd = 0
            for eq in equity_curve:
                peak = max(peak, eq)
                dd = (peak - eq) / peak * 100
                max_dd = max(max_dd, dd)
            
            result.max_drawdown = max_dd
            result.total_return = (capital - initial_capital) / initial_capital * 100
            result.expectancy = (result.win_rate / 100 * result.avg_win) - ((100 - result.win_rate) / 100 * result.avg_loss)
        
        return result
    
    def validate(self, df: pd.DataFrame, signal_func) -> ValidationResult:
        """Walk-Forward validasyonu yap."""
        result = ValidationResult()
        
        # Veriyi böl
        in_sample, out_of_sample = self.split_data(df)
        
        # Minimum gün kontrolü
        if len(out_of_sample) < self.min_forward_days:
            result.reason = f"Out-of-sample yetersiz: {len(out_of_sample)} mum (min: {self.min_forward_days})"
            return result
        
        # In-sample backtest
        result.in_sample = self.backtest_strategy(in_sample, signal_func)
        
        # Out-of-sample backtest
        result.out_of_sample = self.backtest_strategy(out_of_sample, signal_func)
        
        # Validasyon kriterleri
        oos = result.out_of_sample
        
        if oos.total_trades < 10:
            result.reason = f"Yetersiz trade sayısı: {oos.total_trades}"
            return result
        
        if oos.sharpe_ratio < self.min_sharpe:
            result.reason = f"OOS Sharpe düşük: {oos.sharpe_ratio:.2f} < {self.min_sharpe}"
            return result
        
        if oos.profit_factor < self.min_profit_factor:
            result.reason = f"OOS Profit Factor düşük: {oos.profit_factor:.2f} < {self.min_profit_factor}"
            return result
        
        # Overfitting kontrolü
        if result.in_sample and result.in_sample.sharpe_ratio > 0:
            result.overfitting_score = oos.sharpe_ratio / result.in_sample.sharpe_ratio
            if result.overfitting_score < 0.5:
                result.reason = f"Overfitting riski: {result.overfitting_score:.2f}"
                return result
        
        result.is_valid = True
        result.reason = "Validasyon başarılı"
        
        return result


def simple_signal_func(df: pd.DataFrame) -> str:
    """Basit sinyal fonksiyonu (test için)."""
    if len(df) < 20:
        return "NONE"
    
    closes = df["close"].values
    
    # EMA 9/21
    ema9 = pd.Series(closes).ewm(span=9).mean().values
    ema21 = pd.Series(closes).ewm(span=21).mean().values
    
    # RSI
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.mean(gain[-14:])
    avg_loss = np.mean(loss[-14:])
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # Sinyal
    if ema9[-1] > ema21[-1] and rsi < 70:
        return "LONG"
    elif ema9[-1] < ema21[-1] and rsi > 30:
        return "SHORT"
    
    return "NONE"
