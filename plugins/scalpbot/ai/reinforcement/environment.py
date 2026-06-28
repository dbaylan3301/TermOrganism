"""Trading environment for RL agents."""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class TradingState:
    """Current state of trading environment."""
    price: float
    position: int  # 0: flat, 1: long, -1: short
    balance: float
    unrealized_pnl: float
    indicators: np.ndarray


@dataclass
class TradingAction:
    """Trading action."""
    action_type: str  # "BUY", "SELL", "HOLD"
    size: float = 1.0


class CryptoTradingEnv:
    """Crypto trading environment for RL."""

    ACTIONS = ["HOLD", "BUY", "SELL"]
    MAX_POSITION = 1.0
    TRANSACTION_COST = 0.001  # 0.1%

    def __init__(self, data: np.ndarray, initial_balance: float = 10000.0):
        self.data = data
        self.initial_balance = initial_balance
        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.total_trades = 0
        self.winning_trades = 0

        return self._get_state()

    def _get_state(self) -> np.ndarray:
        """Get current state."""
        price = self.data[self.current_step]

        # Simple indicators
        if self.current_step >= 20:
            recent_prices = self.data[self.current_step-20:self.current_step+1]
            sma_20 = np.mean(recent_prices)
            momentum = (price - recent_prices[0]) / recent_prices[0]
        else:
            sma_20 = price
            momentum = 0.0

        state = np.array([
            price / self.data[0],  # Normalized price
            self.position,
            self.balance / self.initial_balance,
            sma_20 / price if price > 0 else 1.0,
            momentum
        ])

        return state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, dict]:
        """Take action and return next state, reward, done, info."""
        current_price = self.data[self.current_step]
        next_price = self.data[min(self.current_step + 1, len(self.data) - 1)]

        reward = 0.0
        done = False

        # Execute action
        if action == 1:  # BUY
            if self.position <= 0:
                # Close short if exists
                if self.position < 0:
                    pnl = (self.entry_price - current_price) * abs(self.position)
                    self.balance += pnl
                    reward += pnl / self.balance

                # Open long
                self.position = self.MAX_POSITION
                self.entry_price = current_price
                self.balance -= self.TRANSACTION_COST * current_price
                self.total_trades += 1

        elif action == 2:  # SELL
            if self.position >= 0:
                # Close long if exists
                if self.position > 0:
                    pnl = (current_price - self.entry_price) * self.position
                    self.balance += pnl
                    reward += pnl / self.balance
                    if pnl > 0:
                        self.winning_trades += 1

                # Open short
                self.position = -self.MAX_POSITION
                self.entry_price = current_price
                self.balance -= self.TRANSACTION_COST * current_price
                self.total_trades += 1

        # Update step
        self.current_step += 1

        # Calculate unrealized P&L
        if self.position > 0:
            unrealized = (next_price - self.entry_price) * self.position
        elif self.position < 0:
            unrealized = (self.entry_price - next_price) * abs(self.position)
        else:
            unrealized = 0.0

        # Check if done
        if self.current_step >= len(self.data) - 1:
            done = True
            # Final settlement
            if self.position > 0:
                final_pnl = (next_price - self.entry_price) * self.position
                self.balance += final_pnl
            elif self.position < 0:
                final_pnl = (self.entry_price - next_price) * abs(self.position)
                self.balance += final_pnl

        # Additional reward shaping
        reward += unrealized / self.balance * 0.1

        info = {
            "balance": self.balance,
            "position": self.position,
            "total_trades": self.total_trades,
            "win_rate": self.winning_trades / max(self.total_trades, 1)
        }

        return self._get_state(), reward, done, info

    @property
    def state_size(self) -> int:
        return 5

    @property
    def action_size(self) -> int:
        return len(self.ACTIONS)
