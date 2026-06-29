"""Backtest Module - Professional Backtesting."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

@dataclass
class BacktestConfig:
    initial_capital: float = 10000.0
    position_size: float = 0.1  # %10 of capital
    max_positions: int = 3
    stop_loss: float = 0.02  # %2
    take_profit: float = 0.04  # %4
    commission: float = 0.001  # %0.1
    slippage: float = 0.0005  # %0.05
    funding_rate: float = 0.0001  # hourly
    enable_short: bool = True

@dataclass
class Trade:
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    status: str = "open"  # "open", "closed"

@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    equity_curve: List[float]
    trades: List[Trade]
    monthly_returns: Dict[str, float]
    stats: Dict

class BacktestEngine:
    """Profesyonel backtest motoru."""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades = []
        self.equity_curve = []
        self.positions = {}
    
    def run(self, df: pd.DataFrame, signal_func: Callable, 
            symbol: str = "BTCUSDT") -> BacktestResult:
        """Backtest çalıştır."""
        # Başlangıç
        capital = self.config.initial_capital
        self.trades = []
        self.equity_curve = [capital]
        self.positions = {}
        
        # Sinyal üret
        signals = []
        for i in range(len(df)):
            try:
                signal = signal_func(df.iloc[:i+1])
                signals.append(signal)
            except Exception:
                signals.append({"direction": "NEUTRAL", "confidence": 0})
        
        # Her bar için
        for i in range(1, len(df)):
            current_price = df['close'].iloc[i]
            current_time = df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now()
            
            signal = signals[i]
            
            # Açık pozisyonları güncelle
            self._update_positions(current_price, current_time, capital)
            
            # Sinyal varsa pozisyon aç
            if signal.get("direction") == "LONG" and signal.get("confidence", 0) > 60:
                if "LONG" not in self.positions and len(self.positions) < self.config.max_positions:
                    self._open_position(symbol, "LONG", current_price, current_time, capital)
            
            elif signal.get("direction") == "SHORT" and signal.get("confidence", 0) > 60:
                if "SHORT" not in self.positions and len(self.positions) < self.config.max_positions:
                    if self.config.enable_short:
                        self._open_position(symbol, "SHORT", current_price, current_time, capital)
            
            # Equity curve güncelle
            equity = self._calculate_equity(current_price, capital)
            self.equity_curve.append(equity)
        
        # Tüm pozisyonları kapat
        if len(df) > 0:
            final_price = df['close'].iloc[-1]
            final_time = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else datetime.now()
            self._close_all_positions(final_price, final_time, capital)
        
        # Sonuçları hesapla
        return self._calculate_results(capital)
    
    def _open_position(self, symbol: str, side: str, price: float, 
                       time: datetime, capital: float):
        """Pozisyon aç."""
        # Slippage
        if side == "LONG":
            entry_price = price * (1 + self.config.slippage)
        else:
            entry_price = price * (1 - self.config.slippage)
        
        # Quantity
        position_value = capital * self.config.position_size
        quantity = position_value / entry_price
        
        # Commission
        fees = position_value * self.config.commission
        
        # Position key
        pos_key = f"{symbol}_{side}"
        
        self.positions[pos_key] = Trade(
            entry_time=time,
            exit_time=None,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=None,
            quantity=quantity,
            fees=fees,
            status="open"
        )
    
    def _update_positions(self, current_price: float, time: datetime, capital: float):
        """Açık pozisyonları güncelle."""
        positions_to_close = []
        
        for pos_key, trade in self.positions.items():
            if trade.status != "open":
                continue
            
            # PnL hesapla
            if trade.side == "LONG":
                unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
                pnl_pct = (current_price / trade.entry_price - 1) * 100
            else:
                unrealized_pnl = (trade.entry_price - current_price) * trade.quantity
                pnl_pct = (trade.entry_price / current_price - 1) * 100
            
            # Stop loss / Take profit kontrolü
            if pnl_pct <= -self.config.stop_loss * 100 or pnl_pct >= self.config.take_profit * 100:
                positions_to_close.append((pos_key, current_price, time, pnl_pct))
        
        # Pozisyonları kapat
        for pos_key, price, close_time, pnl_pct in positions_to_close:
            self._close_position(pos_key, price, close_time, pnl_pct)
    
    def _close_position(self, pos_key: str, price: float, time: datetime, pnl_pct: float):
        """Pozisyonu kapat."""
        trade = self.positions[pos_key]
        
        # Exit price with slippage
        if trade.side == "LONG":
            exit_price = price * (1 - self.config.slippage)
        else:
            exit_price = price * (1 + self.config.slippage)
        
        # PnL
        if trade.side == "LONG":
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        # Fees
        fees = trade.quantity * exit_price * self.config.commission
        total_fees = trade.fees + fees
        
        # Funding cost (simplified)
        duration_hours = (time - trade.entry_time).total_seconds() / 3600
        funding_cost = trade.quantity * trade.entry_price * self.config.funding_rate * duration_hours
        
        # Final PnL
        final_pnl = pnl - total_fees - funding_cost
        
        trade.exit_time = time
        trade.exit_price = exit_price
        trade.pnl = final_pnl
        trade.pnl_pct = pnl_pct
        trade.fees = total_fees
        trade.status = "closed"
        
        self.trades.append(trade)
        del self.positions[pos_key]
    
    def _close_all_positions(self, price: float, time: datetime, capital: float):
        """Tüm pozisyonları kapat."""
        pos_keys = list(self.positions.keys())
        for pos_key in pos_keys:
            trade = self.positions[pos_key]
            if trade.side == "LONG":
                pnl_pct = (price / trade.entry_price - 1) * 100
            else:
                pnl_pct = (trade.entry_price / price - 1) * 100
            self._close_position(pos_key, price, time, pnl_pct)
    
    def _calculate_equity(self, current_price: float, capital: float) -> float:
        """Toplam equity'yi hesapla."""
        equity = capital
        
        for trade in self.positions.values():
            if trade.status == "open":
                if trade.side == "LONG":
                    unrealized = (current_price - trade.entry_price) * trade.quantity
                else:
                    unrealized = (trade.entry_price - current_price) * trade.quantity
                equity += unrealized
        
        return equity
    
    def _calculate_results(self, initial_capital: float) -> BacktestResult:
        """Backtest sonuçlarını hesapla."""
        if not self.equity_curve:
            return BacktestResult(
                total_return=0, annual_return=0, sharpe_ratio=0,
                sortino_ratio=0, max_drawdown=0, win_rate=0,
                profit_factor=0, total_trades=0, avg_trade_duration=0,
                equity_curve=[], trades=[], monthly_returns={}, stats={}
            )
        
        equity = np.array(self.equity_curve)
        
        # Returns
        returns = np.diff(equity) / equity[:-1]
        
        # Total return
        total_return = (equity[-1] / equity[0] - 1) * 100
        
        # Annual return (assuming 252 trading days)
        n_days = len(equity)
        annual_return = ((equity[-1] / equity[0]) ** (252 / max(n_days, 1)) - 1) * 100
        
        # Sharpe ratio
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and np.std(downside_returns) > 0:
            sortino_ratio = np.mean(returns) / np.std(downside_returns) * np.sqrt(252)
        else:
            sortino_ratio = 0
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) * 100 if len(drawdown) > 0 else 0
        
        # Trade stats
        closed_trades = [t for t in self.trades if t.status == "closed"]
        total_trades = len(closed_trades)
        
        if total_trades > 0:
            winning_trades = [t for t in closed_trades if t.pnl > 0]
            win_rate = len(winning_trades) / total_trades * 100
            
            gross_profit = sum(t.pnl for t in winning_trades)
            gross_loss = abs(sum(t.pnl for t in closed_trades if t.pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Avg trade duration
            durations = []
            for t in closed_trades:
                if t.exit_time and t.entry_time:
                    duration = (t.exit_time - t.entry_time).total_seconds() / 3600
                    durations.append(duration)
            avg_trade_duration = np.mean(durations) if durations else 0
        else:
            win_rate = 0
            profit_factor = 0
            avg_trade_duration = 0
        
        # Monthly returns
        monthly_returns = self._calculate_monthly_returns(equity)
        
        # Stats
        stats = {
            'total_pnl': sum(t.pnl for t in closed_trades),
            'avg_pnl_per_trade': np.mean([t.pnl for t in closed_trades]) if closed_trades else 0,
            'best_trade': max([t.pnl for t in closed_trades]) if closed_trades else 0,
            'worst_trade': min([t.pnl for t in closed_trades]) if closed_trades else 0,
            'avg_win': np.mean([t.pnl for t in closed_trades if t.pnl > 0]) if winning_trades else 0,
            'avg_loss': np.mean([t.pnl for t in closed_trades if t.pnl < 0]) if closed_trades else 0,
            'total_fees': sum(t.fees for t in closed_trades)
        }
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            avg_trade_duration=avg_trade_duration,
            equity_curve=self.equity_curve,
            trades=closed_trades,
            monthly_returns=monthly_returns,
            stats=stats
        )
    
    def _calculate_monthly_returns(self, equity: np.ndarray) -> Dict[str, float]:
        """Aylık getirileri hesapla."""
        if len(equity) < 30:
            return {}
        
        # Simplified: divide into chunks
        chunk_size = len(equity) // 12
        monthly_returns = {}
        
        for i in range(12):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(equity))
            if start < end and equity[start] > 0:
                monthly_return = (equity[end-1] / equity[start] - 1) * 100
                monthly_returns[f"Month_{i+1}"] = round(monthly_return, 2)
        
        return monthly_returns

class MonteCarloSimulator:
    """Monte Carlo simülasyonu."""
    
    def __init__(self, n_simulations: int = 1000):
        self.n_simulations = n_simulations
    
    def simulate(self, trades: List[Trade], initial_capital: float) -> Dict:
        """Monte Carlo simülasyonu çalıştır."""
        if not trades:
            return {"simulations": [], "stats": {}}
        
        # Trade PnL'lerini al
        pnls = [t.pnl for t in trades]
        
        simulations = []
        for _ in range(self.n_simulations):
            # Rastgele trade sırası
            shuffled = np.random.permutation(pnls)
            
            # Equity curve oluştur
            equity = [initial_capital]
            for pnl in shuffled:
                equity.append(equity[-1] + pnl)
            
            simulations.append(equity)
        
        # İstatistikler
        final_equities = [sim[-1] for sim in simulations]
        
        stats = {
            'mean_final_equity': np.mean(final_equities),
            'median_final_equity': np.median(final_equities),
            'std_final_equity': np.std(final_equities),
            'percentile_5': np.percentile(final_equities, 5),
            'percentile_95': np.percentile(final_equities, 95),
            'probability_of_profit': sum(1 for e in final_equities if e > initial_capital) / self.n_simulations * 100,
            'max_drawdown_avg': self._avg_max_drawdown(simulations)
        }
        
        return {
            "simulations": simulations,
            "stats": stats
        }
    
    def _avg_max_drawdown(self, simulations: List[List[float]]) -> float:
        """Ortalama max drawdown."""
        drawdowns = []
        
        for sim in simulations:
            equity = np.array(sim)
            returns = np.diff(equity) / equity[:-1]
            cumulative = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = running_max - cumulative
            max_dd = np.max(drawdown) * 100 if len(drawdown) > 0 else 0
            drawdowns.append(max_dd)
        
        return np.mean(drawdowns)
