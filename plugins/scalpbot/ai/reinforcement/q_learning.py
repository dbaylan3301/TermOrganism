"""Q-Learning agent for trading."""

import numpy as np
from typing import Tuple
from .environment import CryptoTradingEnv


class QLearningAgent:
    """Q-Learning agent for trading."""

    def __init__(self, state_size: int, action_size: int,
                 learning_rate: float = 0.1, discount_factor: float = 0.95,
                 epsilon: float = 1.0, epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        # Discretize state space
        self.q_table = {}
        self.bins = self._create_bins()

    def _create_bins(self) -> list:
        """Create bins for state discretization."""
        bins = []
        for i in range(self.state_size):
            if i == 0:  # Price ratio
                bins.append(np.linspace(0.8, 1.2, 20))
            elif i == 1:  # Position
                bins.append(np.array([-1, 0, 1]))
            elif i == 2:  # Balance ratio
                bins.append(np.linspace(0.5, 1.5, 10))
            else:
                bins.append(np.linspace(-0.5, 0.5, 10))
        return bins

    def _discretize(self, state: np.ndarray) -> tuple:
        """Discretize continuous state."""
        discrete = []
        for i, (val, bin_edges) in enumerate(zip(state, self.bins)):
            idx = np.digitize(val, bin_edges) - 1
            idx = max(0, min(idx, len(bin_edges) - 1))
            discrete.append(idx)
        return tuple(discrete)

    def get_q_value(self, state: tuple, action: int) -> float:
        """Get Q-value for state-action pair."""
        key = (state, action)
        return self.q_table.get(key, 0.0)

    def choose_action(self, state: np.ndarray) -> int:
        """Choose action using epsilon-greedy policy."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)

        discrete_state = self._discretize(state)
        q_values = [self.get_q_value(discrete_state, a)
                   for a in range(self.action_size)]
        return np.argmax(q_values)

    def learn(self, state: np.ndarray, action: int, reward: float,
              next_state: np.ndarray, done: bool):
        """Update Q-value."""
        discrete_state = self._discretize(state)
        discrete_next_state = self._discretize(next_state)

        # Current Q-value
        current_q = self.get_q_value(discrete_state, action)

        # Best next Q-value
        if done:
            target_q = reward
        else:
            next_q_values = [self.get_q_value(discrete_next_state, a)
                           for a in range(self.action_size)]
            target_q = reward + self.discount_factor * max(next_q_values)

        # Update Q-value
        new_q = current_q + self.learning_rate * (target_q - current_q)
        self.q_table[(discrete_state, action)] = new_q

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def train(self, env: CryptoTradingEnv, episodes: int = 100) -> dict:
        """Train the agent."""
        scores = []

        for episode in range(episodes):
            state = env.reset()
            total_reward = 0
            steps = 0

            done = False
            while not done:
                action = self.choose_action(state)
                next_state, reward, done, info = env.step(action)
                self.learn(state, action, reward, next_state, done)

                state = next_state
                total_reward += reward
                steps += 1

            scores.append(total_reward)

            if (episode + 1) % 10 == 0:
                avg_score = np.mean(scores[-10:])
                print(f"Episode {episode + 1}/{episodes}, Avg Score: {avg_score:.4f}")

        return {
            "status": "trained",
            "episodes": episodes,
            "final_epsilon": self.epsilon,
            "avg_score": np.mean(scores[-10:]) if scores else 0
        }
