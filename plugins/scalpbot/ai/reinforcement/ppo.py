"""PPO (Proximal Policy Optimization) agent."""

import numpy as np
from typing import Tuple, List
from .environment import CryptoTradingEnv


class PPOAgent:
    """PPO agent for trading."""

    def __init__(self, state_size: int, action_size: int,
                 learning_rate: float = 0.001, clip_epsilon: float = 0.2,
                 gamma: float = 0.99, gae_lambda: float = 0.95):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.clip_epsilon = clip_epsilon
        self.gamma = gamma
        self.gae_lambda = gae_lambda

        # Simple policy and value networks (no PyTorch)
        self.policy_weights = np.random.randn(state_size, action_size) * 0.01
        self.value_weights = np.random.randn(state_size, 1) * 0.01

        # Experience buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []

    def softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax function."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def get_policy(self, state: np.ndarray) -> np.ndarray:
        """Get action probabilities."""
        logits = np.dot(state, self.policy_weights)
        return self.softmax(logits)

    def get_value(self, state: np.ndarray) -> float:
        """Get state value."""
        return float(np.dot(state, self.value_weights).item())

    def choose_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """Choose action and return action, log_prob, value."""
        probs = self.get_policy(state)

        # Sample action
        action = np.random.choice(self.action_size, p=probs)

        # Calculate log probability
        log_prob = np.log(probs[action] + 1e-10)

        # Get value
        value = self.get_value(state)

        return action, log_prob, value

    def compute_gae(self, rewards: List[float], values: List[float],
                    next_value: float) -> List[float]:
        """Compute Generalized Advantage Estimation."""
        advantages = []
        gae = 0

        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_val = next_value
            else:
                next_val = values[t + 1]

            delta = rewards[t] + self.gamma * next_val - values[t]
            gae = delta + self.gamma * self.gae_lambda * gae
            advantages.insert(0, gae)

        return advantages

    def update(self, next_value: float):
        """Update policy and value networks."""
        if len(self.states) == 0:
            return

        # Convert to arrays
        states = np.array(self.states)
        actions = np.array(self.actions)
        old_log_probs = np.array(self.log_probs)
        values = np.array(self.values)

        # Compute advantages
        advantages = self.compute_gae(self.rewards, values, next_value)
        returns = advantages + values

        # Normalize advantages
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        # Simple gradient update (no autograd)
        for i in range(len(states)):
            state = states[i]
            action = actions[i]
            advantage = advantages[i]
            return_val = returns[i]

            # Policy gradient
            probs = self.get_policy(state)
            grad_log_probs = -probs
            grad_log_probs[action] += 1
            policy_grad = advantage * grad_log_probs

            # Value gradient
            value_pred = self.get_value(state)
            value_grad = (return_val - value_pred) * state

            # Update weights
            self.policy_weights += self.learning_rate * np.outer(state, policy_grad)
            self.value_weights += self.learning_rate * np.outer(state,
                np.array([return_val - value_pred]))

        # Clear buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []

    def train(self, env: CryptoTradingEnv, episodes: int = 100,
              update_interval: int = 20) -> dict:
        """Train the agent."""
        scores = []

        for episode in range(episodes):
            state = env.reset()
            total_reward = 0

            done = False
            while not done:
                action, log_prob, value = self.choose_action(state)

                next_state, reward, done, info = env.step(action)

                # Store experience
                self.states.append(state)
                self.actions.append(action)
                self.rewards.append(reward)
                self.values.append(value)
                self.log_probs.append(log_prob)

                state = next_state
                total_reward += reward

                # Update periodically
                if len(self.states) >= update_interval:
                    next_val = self.get_value(next_state)
                    self.update(next_val)

            scores.append(total_reward)

            if (episode + 1) % 10 == 0:
                avg_score = np.mean(scores[-10:])
                print(f"Episode {episode + 1}/{episodes}, Avg Score: {avg_score:.4f}")

        return {
            "status": "trained",
            "episodes": episodes,
            "avg_score": np.mean(scores[-10:]) if scores else 0
        }
