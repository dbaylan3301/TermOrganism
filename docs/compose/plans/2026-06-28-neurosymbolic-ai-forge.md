# Neuro-Symbolic AI & AI Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Neuro-Symbolic AI (neural + symbolic reasoning), deeper neural architecture, and AI Forge interactive environment to scalpbot.

**Architecture:** ScalpBrain deep model with CNN+LSTM+Transformer, SymbolicRuleEngine for trading rules, AIForge for interactive coding/monitoring, and hybrid fusion.

**Tech Stack:** PyTorch, NumPy, Pandas, custom Neuro-Symbolic framework

---

## Task 1: ScalpBrain Deep Neural Architecture

**Covers:** Deep neural network with CNN, LSTM, Transformer, Attention, Actor-Critic

**Files:**
- Create: `plugins/scalpbot/ai/neural/scalp_brain.py`

- [ ] **Step 1: Create ScalpBrain model**

```python
# plugins/scalpbot/ai/neural/scalp_brain.py
"""ScalpBrain - Deep Neural Architecture for trading."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BrainOutput:
    """ScalpBrain output."""
    meta_prediction: torch.Tensor  # [batch, 3] - Buy/Sell/Hold probabilities
    actor_logits: torch.Tensor     # [batch, 3] - RL action logits
    critic_value: torch.Tensor     # [batch, 1] - State value
    attention_weights: Optional[torch.Tensor] = None
    uncertainty: Optional[torch.Tensor] = None


class ResidualBlock(nn.Module):
    """Residual connection block."""
    
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv1d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(channels)
        self.conv2 = nn.Conv1d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return F.relu(out + residual)


class DilatedConvBlock(nn.Module):
    """Dilated convolution for wider receptive field."""
    
    def __init__(self, in_channels: int, out_channels: int, dilation: int = 1):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=3, 
                              padding=dilation, dilation=dilation)
        self.bn = nn.BatchNorm1d(out_channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.bn(self.conv(x)))


class ScalpBrain(nn.Module):
    """
    ScalpBrain - Human Brain-Inspired Deep Neural Architecture.
    
    Components:
    - CNN Feature Extractor (Sensory Cortex)
    - Stacked LSTM (Hippocampus/Temporal Lobe)
    - Transformer Encoder (Association Areas)
    - Multi-Head Attention (Attention Mechanism)
    - Meta Output Head (Decision Making)
    - Actor-Critic Heads (RL/Prefrontal Cortex)
    """
    
    def __init__(
        self,
        input_dim: int = 64,
        hidden_dim: int = 512,
        num_lstm_layers: int = 4,
        num_transformer_layers: int = 6,
        num_heads: int = 8,
        dropout: float = 0.3,
        num_actions: int = 3
    ):
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # ==================== CNN FEATURE EXTRACTOR (Sensory Cortex) ====================
        self.cnn = nn.Sequential(
            # First conv block
            nn.Conv1d(input_dim, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout * 0.5),
            
            # Residual blocks
            ResidualBlock(128),
            ResidualBlock(128),
            
            # Second conv block with dilation
            DilatedConvBlock(128, 256, dilation=2),
            ResidualBlock(256),
            
            # Third conv block
            DilatedConvBlock(256, 512, dilation=4),
            ResidualBlock(512),
            
            # Output projection
            nn.Conv1d(512, hidden_dim, kernel_size=1),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        
        # ==================== TEMPORAL MEMORY (Hippocampus) ====================
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_lstm_layers,
            batch_first=True,
            dropout=dropout if num_lstm_layers > 1 else 0,
            bidirectional=True
        )
        
        # LSTM output projection (bidirectional -> hidden_dim)
        self.lstm_proj = nn.Linear(hidden_dim * 2, hidden_dim)
        
        # ==================== TRANSFORMER ENCODER (Association Areas) ====================
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True  # Pre-norm for better training
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, 
            num_layers=num_transformer_layers
        )
        
        # ==================== MULTI-HEAD ATTENTION (Attention Mechanism) ====================
        self.self_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        self.attention_norm = nn.LayerNorm(hidden_dim)
        
        # ==================== META OUTPUT HEAD (Decision Making) ====================
        self.meta_head = nn.Sequential(
            nn.Linear(hidden_dim, 512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, 64),
            nn.GELU(),
            nn.Linear(64, num_actions)  # Buy, Sell, Hold
        )
        
        # ==================== ACTOR-CRITIC HEADS (RL/Prefrontal Cortex) ====================
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, num_actions)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, 1)
        )
        
        # ==================== UNCERTAINTY ESTIMATION (Amygdala) ====================
        self.uncertainty_head = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.GELU(),
            nn.Linear(128, num_actions),
            nn.Softmax(dim=-1)
        )
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with Xavier/Kaiming."""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> BrainOutput:
        """
        Forward pass.
        
        Args:
            x: [batch_size, seq_len, input_dim]
            
        Returns:
            BrainOutput with all predictions
        """
        batch_size, seq_len, _ = x.shape
        
        # CNN Feature Extraction (Sensory Cortex)
        # [batch, seq, features] -> [batch, features, seq]
        cnn_input = x.transpose(1, 2)
        cnn_out = self.cnn(cnn_input)
        # [batch, hidden, seq] -> [batch, seq, hidden]
        cnn_out = cnn_out.transpose(1, 2)
        
        # LSTM Temporal Memory (Hippocampus)
        lstm_out, (h_n, c_n) = self.lstm(cnn_out)
        lstm_out = self.lstm_proj(lstm_out)
        
        # Transformer Encoding (Association Areas)
        transformer_out = self.transformer(lstm_out)
        
        # Self-Attention (Attention Mechanism)
        attn_out, attn_weights = self.self_attention(
            transformer_out, transformer_out, transformer_out
        )
        attn_out = self.attention_norm(transformer_out + attn_out)
        
        # Get final hidden state
        final_hidden = attn_out[:, -1, :]  # [batch, hidden_dim]
        
        # Meta Prediction (Decision Making)
        meta_pred = self.meta_head(final_hidden)
        
        # Actor-Critic (RL)
        actor_logits = self.actor(final_hidden)
        critic_value = self.critic(final_hidden)
        
        # Uncertainty Estimation (Amygdala)
        uncertainty = self.uncertainty_head(final_hidden)
        
        return BrainOutput(
            meta_prediction=meta_pred,
            actor_logits=actor_logits,
            critic_value=critic_value,
            attention_weights=attn_weights,
            uncertainty=uncertainty
        )
    
    def get_action(self, state: torch.Tensor, temperature: float = 1.0) -> Tuple[int, float, float]:
        """
        Get action with temperature scaling for exploration.
        
        Returns:
            action, probability, value
        """
        with torch.no_grad():
            output = self.forward(state)
            
            # Temperature scaling
            logits = output.actor_logits / temperature
            probs = F.softmax(logits, dim=-1)
            
            # Sample action
            action = torch.multinomial(probs, 1).item()
            prob = probs[0, action].item()
            value = output.critic_value.item()
            
            return action, prob, value
    
    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
```

- [ ] **Step 2: Create neural __init__.py**

```python
# plugins/scalpbot/ai/neural/__init__.py
"""Neural brain modules."""

from .scalp_brain import ScalpBrain, BrainOutput

__all__ = ["ScalpBrain", "BrainOutput"]
```

- [ ] **Step 3: Test ScalpBrain**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
PYTHONPATH=. python -c "
import torch
from plugins.scalpbot.ai.neural.scalp_brain import ScalpBrain

model = ScalpBrain(input_dim=32, hidden_dim=128, num_lstm_layers=2, num_transformer_layers=2)
print(f'Total parameters: {model.count_parameters():,}')

# Test forward pass
x = torch.randn(4, 50, 32)  # batch=4, seq=50, features=32
output = model(x)
print(f'Meta prediction shape: {output.meta_prediction.shape}')
print(f'Actor logits shape: {output.actor_logits.shape}')
print(f'Critic value shape: {output.critic_value.shape}')
print(f'Uncertainty shape: {output.uncertainty.shape}')
"
```

- [ ] **Step 4: Commit**

```bash
git add plugins/scalpbot/ai/neural/
git commit -m "feat: add ScalpBrain deep neural architecture"
```

---

## Task 2: Neuro-Symbolic Rule Engine

**Covers:** Symbolic reasoning with trading rules

**Files:**
- Create: `plugins/scalpbot/ai/symbolic/rule_engine.py`
- Create: `plugins/scalpbot/ai/symbolic/knowledge_base.py`
- Create: `plugins/scalpbot/ai/symbolic/fuzzy_logic.py`

- [ ] **Step 1: Create rule_engine.py**

```python
# plugins/scalpbot/ai/symbolic/rule_engine.py
"""Symbolic Rule Engine for trading decisions."""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class RulePriority(Enum):
    """Rule priority levels."""
    CRITICAL = 100  # Risk rules - always enforced
    HIGH = 80       # Entry rules
    MEDIUM = 60     # Filter rules
    LOW = 40        # Enhancement rules


@dataclass
class Rule:
    """Trading rule."""
    name: str
    condition: callable
    action: str
    priority: RulePriority
    description: str
    enabled: bool = True


@dataclass
class RuleResult:
    """Result of rule evaluation."""
    rule_name: str
    triggered: bool
    action: str
    confidence: float
    explanation: str


@dataclass
class SymbolicDecision:
    """Symbolic reasoning output."""
    action: str  # "LONG", "SHORT", "HOLD", "REDUCE", "EXIT"
    confidence: float
    position_size_modifier: float  # 0.0 to 1.0
    rules_triggered: List[RuleResult]
    explanation: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "EXTREME"


class SymbolicRuleEngine:
    """
    Symbolic reasoning engine for trading.
    Implements if-then rules with fuzzy logic.
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default trading rules."""
        
        # CRITICAL RISK RULES
        self.add_rule(Rule(
            name="max_drawdown_check",
            condition=lambda ctx: ctx.get("drawdown_pct", 0) < 5.0,
            action="ALLOW",
            priority=RulePriority.CRITICAL,
            description="Maximum 5% drawdown allowed"
        ))
        
        self.add_rule(Rule(
            name="position_size_check",
            condition=lambda ctx: ctx.get("position_size_pct", 0) < 2.0,
            action="ALLOW",
            priority=RulePriority.CRITICAL,
            description="Maximum 2% position size"
        ))
        
        # HIGH PRIORITY ENTRY RULES
        self.add_rule(Rule(
            name="ema_crossover_confirm",
            condition=lambda ctx: ctx.get("ema_score", 0) > 25,
            action="CONFIRM_LONG",
            priority=RulePriority.HIGH,
            description="EMA crossover must be confirmed"
        ))
        
        self.add_rule(Rule(
            name="volume_spike_required",
            condition=lambda ctx: ctx.get("volume_score", 0) > 20,
            action="CONFIRM_VOLUME",
            priority=RulePriority.HIGH,
            description="Volume spike required for entry"
        ))
        
        self.add_rule(Rule(
            name="rsi_not_overbought",
            condition=lambda ctx: 30 < ctx.get("rsi", 50) < 65,
            action="CONFIRM_RSI",
            priority=RulePriority.HIGH,
            description="RSI must not be overbought/oversold"
        ))
        
        # MEDIUM PRIORITY FILTER RULES
        self.add_rule(Rule(
            name="atr_volatility_check",
            condition=lambda ctx: ctx.get("atr_pct", 0) < 0.5,
            action="FILTER_VOLATILITY",
            priority=RulePriority.MEDIUM,
            description="ATR volatility must be within limits"
        ))
        
        self.add_rule(Rule(
            name="risk_reward_check",
            condition=lambda ctx: ctx.get("risk_reward", 0) >= 2.0,
            action="CONFIRM_RR",
            priority=RulePriority.MEDIUM,
            description="Risk/Reward must be at least 1:2"
        ))
        
        # LOW PRIORITY ENHANCEMENT RULES
        self.add_rule(Rule(
            name="momentum_boost",
            condition=lambda ctx: ctx.get("momentum_score", 0) > 8,
            action="BOOST_CONFIDENCE",
            priority=RulePriority.LOW,
            description="High momentum increases confidence"
        ))
        
        self.add_rule(Rule(
            name="pattern_boost",
            condition=lambda ctx: ctx.get("has_bullish_pattern", False),
            action="BOOST_CONFIDENCE",
            priority=RulePriority.LOW,
            description="Bullish pattern boosts confidence"
        ))
    
    def add_rule(self, rule: Rule):
        """Add a rule to the engine."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority.value, reverse=True)
    
    def evaluate(self, context: Dict[str, Any]) -> SymbolicDecision:
        """
        Evaluate all rules against context.
        
        Args:
            context: Dictionary with market data and indicators
            
        Returns:
            SymbolicDecision with action and explanation
        """
        results: List[RuleResult] = []
        action_votes = {"LONG": 0, "SHORT": 0, "HOLD": 0}
        confidence_modifiers = []
        position_modifier = 1.0
        risk_level = "LOW"
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                triggered = rule.condition(context)
            except Exception:
                triggered = False
            
            result = RuleResult(
                rule_name=rule.name,
                triggered=triggered,
                action=rule.action,
                confidence=1.0 if triggered else 0.0,
                explanation=f"{'✓' if triggered else '✗'} {rule.description}"
            )
            results.append(result)
            
            if triggered:
                # Track action votes
                if "LONG" in rule.action:
                    action_votes["LONG"] += rule.priority.value
                elif "SHORT" in rule.action:
                    action_votes["SHORT"] += rule.priority.value
                elif "HOLD" in rule.action:
                    action_votes["HOLD"] += rule.priority.value
                
                # Boost confidence
                if "BOOST" in rule.action:
                    confidence_modifiers.append(0.1)
            else:
                # Critical rules not triggered = risk
                if rule.priority == RulePriority.CRITICAL:
                    risk_level = "EXTREME"
                    position_modifier = 0.0
                elif rule.priority == RulePriority.HIGH:
                    risk_level = "HIGH"
                    position_modifier *= 0.5
        
        # Determine action
        if position_modifier == 0.0:
            final_action = "HOLD"
        elif action_votes["LONG"] > action_votes["SHORT"]:
            final_action = "LONG"
        elif action_votes["SHORT"] > action_votes["LONG"]:
            final_action = "SHORT"
        else:
            final_action = "HOLD"
        
        # Calculate confidence
        total_priority = sum(r.priority.value for r in results if r.triggered)
        max_priority = sum(r.priority.value for r in results)
        base_confidence = total_priority / max_priority if max_priority > 0 else 0.5
        
        # Apply modifiers
        confidence = base_confidence + sum(confidence_modifiers)
        confidence = min(1.0, max(0.0, confidence))
        
        # Build explanation
        triggered_rules = [r for r in results if r.triggered]
        explanation = f"Symbolic Decision: {final_action}\n"
        explanation += f"Rules triggered: {len(triggered_rules)}/{len(results)}\n"
        explanation += f"Risk level: {risk_level}\n"
        explanation += "Key factors:\n"
        for r in triggered_rules[:5]:
            explanation += f"  • {r.explanation}\n"
        
        return SymbolicDecision(
            action=final_action,
            confidence=confidence,
            position_size_modifier=position_modifier,
            rules_triggered=results,
            explanation=explanation,
            risk_level=risk_level
        )
```

- [ ] **Step 2: Create knowledge_base.py**

```python
# plugins/scalpbot/ai/symbolic/knowledge_base.py
"""Trading knowledge base with financial ontology."""

from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class Concept:
    """Financial concept."""
    name: str
    category: str
    description: str
    relationships: List[str]


@dataclass
class Rule:
    """Trading rule from knowledge base."""
    name: str
    condition: str
    action: str
    confidence: float
    source: str


class TradingKnowledgeBase:
    """
    Financial knowledge base with ontology.
    Links market concepts and trading rules.
    """
    
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.rules: List[Rule] = []
        self.relationships: Dict[str, List[str]] = {}
        
        self._build_ontology()
        self._build_rules()
    
    def _build_ontology(self):
        """Build financial concept ontology."""
        
        # Trend concepts
        self.add_concept(Concept(
            name="uptrend",
            category="trend",
            description="Price making higher highs and higher lows",
            relationships=["bullish", "momentum", "breakout"]
        ))
        
        self.add_concept(Concept(
            name="downtrend",
            category="trend",
            description="Price making lower highs and lower lows",
            relationships=["bearish", "momentum", "breakdown"]
        ))
        
        # Indicator concepts
        self.add_concept(Concept(
            name="ema_crossover",
            category="indicator",
            description="Fast EMA crossing above/below slow EMA",
            relationships=["momentum", "trend_change"]
        ))
        
        self.add_concept(Concept(
            name="volume_spike",
            category="volume",
            description="Volume significantly above average",
            relationships=["confirmation", "breakout"]
        ))
        
        # Pattern concepts
        self.add_concept(Concept(
            name="bullish_engulfing",
            category="pattern",
            description="Bullish reversal candlestick pattern",
            relationships=["reversal", "support", "entry_signal"]
        ))
        
        # Risk concepts
        self.add_concept(Concept(
            name="support_level",
            category="risk",
            description="Price level where buying interest is strong",
            relationships=["stop_loss", "risk_management"]
        ))
    
    def add_concept(self, concept: Concept):
        """Add concept to ontology."""
        self.concepts[concept.name] = concept
        for rel in concept.relationships:
            if rel not in self.relationships:
                self.relationships[rel] = []
            self.relationships[rel].append(concept.name)
    
    def _build_rules(self):
        """Build trading rules from knowledge."""
        
        self.rules = [
            Rule("trend_follow", "uptrend AND momentum positive", "LONG", 0.8, "trend_analysis"),
            Rule("reversal_entry", "downtrend AND bullish_pattern", "LONG", 0.7, "pattern_recognition"),
            Rule("volume_breakout", "volume_spike AND breakout", "LONG", 0.75, "volume_analysis"),
            Rule("risk_exit", "stop_loss_hit OR max_drawdown", "EXIT", 0.95, "risk_management"),
            Rule("take_profit", "target_reached OR overbought", "EXIT", 0.85, "profit_taking"),
        ]
    
    def query(self, concept_name: str) -> List[str]:
        """Query related concepts."""
        if concept_name in self.concepts:
            return self.concepts[concept_name].relationships
        return []
    
    def get_rules_for_context(self, context: Dict) -> List[Rule]:
        """Get relevant rules for given context."""
        relevant = []
        for rule in self.rules:
            # Simple keyword matching
            if any(word in str(context).lower() for word in rule.condition.split()):
                relevant.append(rule)
        return relevant
```

- [ ] **Step 3: Create fuzzy_logic.py**

```python
# plugins/scalpbot/ai/symbolic/fuzzy_logic.py
"""Fuzzy logic for trading decisions."""

import numpy as np
from typing import Dict, Tuple


class FuzzyMembership:
    """Fuzzy membership functions."""
    
    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """Triangular membership function."""
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:
            return (c - x) / (c - b)
    
    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """Trapezoidal membership function."""
        if x <= a or x >= d:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        elif b < x <= c:
            return 1.0
        else:
            return (d - x) / (d - c)
    
    @staticmethod
    def gaussian(x: float, mean: float, sigma: float) -> float:
        """Gaussian membership function."""
        return np.exp(-0.5 * ((x - mean) / sigma) ** 2)


class FuzzyTradingSystem:
    """
    Fuzzy logic system for trading.
    Converts crisp values to fuzzy sets and applies rules.
    """
    
    def __init__(self):
        self.mf = FuzzyMembership()
    
    def fuzzify_rsi(self, rsi: float) -> Dict[str, float]:
        """Fuzzify RSI value."""
        return {
            "oversold": self.mf.trapezoidal(rsi, 0, 0, 25, 35),
            "neutral": self.mf.triangular(rsi, 25, 50, 75),
            "overbought": self.mf.trapezoidal(rsi, 65, 75, 100, 100)
        }
    
    def fuzzify_volume(self, volume_ratio: float) -> Dict[str, float]:
        """Fuzzify volume ratio."""
        return {
            "low": self.mf.trapezoidal(volume_ratio, 0, 0, 0.5, 1.0),
            "normal": self.mf.triangular(volume_ratio, 0.5, 1.0, 2.0),
            "high": self.mf.trapezoidal(volume_ratio, 1.5, 2.0, 5.0, 5.0)
        }
    
    def fuzzify_momentum(self, momentum: float) -> Dict[str, float]:
        """Fuzzify momentum value."""
        return {
            "negative": self.mf.trapezoidal(momentum, -1, -1, -0.3, 0),
            "neutral": self.mf.triangular(momentum, -0.3, 0, 0.3),
            "positive": self.mf.trapezoidal(momentum, 0, 0.3, 1, 1)
        }
    
    def apply_rules(self, rsi_fuzzy: Dict, volume_fuzzy: Dict, 
                    momentum_fuzzy: Dict) -> Dict[str, float]:
        """Apply fuzzy rules."""
        rules = {
            "strong_buy": min(rsi_fuzzy["oversold"], volume_fuzzy["high"], momentum_fuzzy["positive"]),
            "buy": min(rsi_fuzzy["oversold"], volume_fuzzy["normal"]),
            "hold": max(rsi_fuzzy["neutral"], min(volume_fuzzy["normal"], momentum_fuzzy["neutral"])),
            "sell": min(rsi_fuzzy["overbought"], volume_fuzzy["normal"]),
            "strong_sell": min(rsi_fuzzy["overbought"], volume_fuzzy["high"], momentum_fuzzy["negative"])
        }
        return rules
    
    def defuzzify(self, rules: Dict[str, float]) -> Tuple[str, float]:
        """Defuzzify to crisp decision."""
        # Weighted average defuzzification
        action_weights = {
            "strong_buy": 2.0,
            "buy": 1.0,
            "hold": 0.0,
            "sell": -1.0,
            "strong_sell": -2.0
        }
        
        weighted_sum = sum(rules[a] * action_weights[a] for a in rules)
        weight_sum = sum(rules.values())
        
        if weight_sum == 0:
            return "hold", 0.5
        
        crisp_value = weighted_sum / weight_sum
        
        if crisp_value > 0.5:
            return "strong_buy", min(0.9, 0.5 + crisp_value * 0.2)
        elif crisp_value > 0.1:
            return "buy", 0.6 + crisp_value * 0.1
        elif crisp_value < -0.5:
            return "strong_sell", min(0.9, 0.5 + abs(crisp_value) * 0.2)
        elif crisp_value < -0.1:
            return "sell", 0.6 + abs(crisp_value) * 0.1
        else:
            return "hold", 0.5
    
    def evaluate(self, rsi: float, volume_ratio: float, 
                momentum: float) -> Tuple[str, float]:
        """Full fuzzy evaluation."""
        rsi_fuzzy = self.fuzzify_rsi(rsi)
        volume_fuzzy = self.fuzzify_volume(volume_ratio)
        momentum_fuzzy = self.fuzzify_momentum(momentum)
        
        rules = self.apply_rules(rsi_fuzzy, volume_fuzzy, momentum_fuzzy)
        return self.defuzzify(rules)
```

- [ ] **Step 4: Create symbolic __init__.py**

```python
# plugins/scalpbot/ai/symbolic/__init__.py
"""Symbolic reasoning modules."""

from .rule_engine import SymbolicRuleEngine, SymbolicDecision
from .knowledge_base import TradingKnowledgeBase
from .fuzzy_logic import FuzzyTradingSystem

__all__ = ["SymbolicRuleEngine", "SymbolicDecision", "TradingKnowledgeBase", "FuzzyTradingSystem"]
```

- [ ] **Step 5: Test symbolic modules**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
PYTHONPATH=. python -c "
from plugins.scalpbot.ai.symbolic.rule_engine import SymbolicRuleEngine
from plugins.scalpbot.ai.symbolic.fuzzy_logic import FuzzyTradingSystem

# Test rule engine
engine = SymbolicRuleEngine()
context = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'risk_reward': 2.2, 'atr_pct': 0.3}
decision = engine.evaluate(context)
print(f'Rule Engine Decision: {decision.action}')
print(f'Confidence: {decision.confidence:.2f}')

# Test fuzzy logic
fuzzy = FuzzyTradingSystem()
action, conf = fuzzy.evaluate(rsi=45, volume_ratio=1.8, momentum=0.15)
print(f'Fuzzy Decision: {action}, Confidence: {conf:.2f}')
"
```

- [ ] **Step 6: Commit**

```bash
git add plugins/scalpbot/ai/symbolic/
git commit -m "feat: add Neuro-Symbolic rule engine with fuzzy logic"
```

---

## Task 3: Neuro-Symbolic Hybrid Model

**Covers:** Fusion of neural and symbolic reasoning

**Files:**
- Create: `plugins/scalpbot/ai/hybrid/neuro_symbolic.py`

- [ ] **Step 1: Create neuro_symbolic.py**

```python
# plugins/scalpbot/ai/hybrid/neuro_symbolic.py
"""Neuro-Symbolic Hybrid Model."""

import torch
import torch.nn as nn
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from ..neural.scalp_brain import ScalpBrain, BrainOutput
from ..symbolic.rule_engine import SymbolicRuleEngine, SymbolicDecision
from ..symbolic.fuzzy_logic import FuzzyTradingSystem


@dataclass
class HybridDecision:
    """Final hybrid decision."""
    action: str
    confidence: float
    neural_confidence: float
    symbolic_confidence: float
    fuzzy_action: str
    position_size: float
    explanation: str
    risk_level: str


class NeuroSymbolicTrader(nn.Module):
    """
    Neuro-Symbolic Hybrid Model.
    Combines deep learning predictions with symbolic reasoning.
    """
    
    def __init__(self, input_dim: int = 64, hidden_dim: int = 256):
        super().__init__()
        
        # Neural Brain
        self.neural_brain = ScalpBrain(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_lstm_layers=2,
            num_transformer_layers=2,
            num_heads=4
        )
        
        # Symbolic Engine
        self.symbolic_engine = SymbolicRuleEngine()
        
        # Fuzzy Logic
        self.fuzzy_system = FuzzyTradingSystem()
        
        # Fusion Layer
        self.fusion = nn.Sequential(
            nn.Linear(3 + 3 + 3, 64),  # neural + symbolic + fuzzy outputs
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.GELU(),
            nn.Linear(32, 3)  # Final action
        )
        
        # Confidence calibrator
        self.confidence_calibrator = nn.Sequential(
            nn.Linear(3, 16),
            nn.GELU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor, 
                indicators: Dict[str, float]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass with hybrid reasoning.
        """
        # Neural prediction
        neural_out = self.neural_brain(x)
        neural_probs = torch.softmax(neural_out.meta_prediction, dim=-1)
        
        # Symbolic decision
        symbolic_decision = self.symbolic_engine.evaluate(indicators)
        symbolic_probs = self._symbolic_to_probs(symbolic_decision)
        
        # Fuzzy decision
        fuzzy_action, fuzzy_conf = self.fuzzy_system.evaluate(
            rsi=indicators.get("rsi", 50),
            volume_ratio=indicators.get("vol_ratio", 1.0),
            momentum=indicators.get("momentum", 0)
        )
        fuzzy_probs = self._fuzzy_to_probs(fuzzy_action, fuzzy_conf)
        
        # Fusion
        combined = torch.cat([
            neural_probs.squeeze(0),
            symbolic_probs,
            fuzzy_probs
        ]).unsqueeze(0)
        
        fused_action = self.fusion(combined)
        
        # Confidence calibration
        confidence = self.confidence_calibrator(
            torch.cat([neural_probs, symbolic_probs.unsqueeze(0), fuzzy_probs.unsqueeze(0)], dim=-1)
        )
        
        return fused_action, confidence
    
    def _symbolic_to_probs(self, decision: SymbolicDecision) -> torch.Tensor:
        """Convert symbolic decision to probabilities."""
        probs = torch.zeros(3)
        if decision.action == "LONG":
            probs[0] = decision.confidence
        elif decision.action == "SHORT":
            probs[1] = decision.confidence
        else:
            probs[2] = decision.confidence
        return probs
    
    def _fuzzy_to_probs(self, action: str, confidence: float) -> torch.Tensor:
        """Convert fuzzy decision to probabilities."""
        probs = torch.zeros(3)
        if "buy" in action:
            probs[0] = confidence
        elif "sell" in action:
            probs[1] = confidence
        else:
            probs[2] = confidence
        return probs
    
    def make_decision(self, market_data: torch.Tensor,
                      indicators: Dict[str, float]) -> HybridDecision:
        """
        Make final hybrid decision.
        """
        with torch.no_grad():
            fused_action, confidence = self.forward(market_data, indicators)
            
            # Get action
            action_probs = torch.softmax(fused_action, dim=-1)
            action_idx = torch.argmax(action_probs).item()
            actions = ["LONG", "SHORT", "HOLD"]
            action = actions[action_idx]
            
            # Get symbolic decision for explanation
            symbolic_decision = self.symbolic_engine.evaluate(indicators)
            
            # Calculate position size
            position_size = symbolic_decision.position_size_modifier
            
            # Build explanation
            explanation = self._build_explanation(
                action, confidence.item(), symbolic_decision, indicators
            )
            
            return HybridDecision(
                action=action,
                confidence=confidence.item(),
                neural_confidence=action_probs[0, action_idx].item(),
                symbolic_confidence=symbolic_decision.confidence,
                fuzzy_action="buy" if action == "LONG" else "sell" if action == "SHORT" else "hold",
                position_size=position_size,
                explanation=explanation,
                risk_level=symbolic_decision.risk_level
            )
    
    def _build_explanation(self, action: str, confidence: float,
                          symbolic: SymbolicDecision, 
                          indicators: Dict) -> str:
        """Build human-readable explanation."""
        lines = [
            f"🧠 Neuro-Symbolic Decision: {action}",
            f"📊 Confidence: {confidence:.1%}",
            f"⚖️ Position Size: {symbolic.position_size_modifier:.0%}",
            f"🎯 Risk Level: {symbolic.risk_level}",
            "",
            "Neural Analysis:",
            f"  • Pattern recognition: Active",
            f"  • Temporal memory: Engaged",
            "",
            "Symbolic Reasoning:",
        ]
        
        for rule in symbolic.rules_triggered[:5]:
            if rule.triggered:
                lines.append(f"  ✓ {rule.explanation}")
        
        return "\n".join(lines)
```

- [ ] **Step 2: Create hybrid __init__.py**

```python
# plugins/scalpbot/ai/hybrid/__init__.py
"""Hybrid Neuro-Symbolic modules."""

from .neuro_symbolic import NeuroSymbolicTrader, HybridDecision

__all__ = ["NeuroSymbolicTrader", "HybridDecision"]
```

- [ ] **Step 3: Test hybrid model**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
PYTHONPATH=. python -c "
import torch
from plugins.scalpbot.ai.hybrid.neuro_symbolic import NeuroSymbolicTrader

model = NeuroSymbolicTrader(input_dim=32, hidden_dim=128)
print(f'Parameters: {model.neural_brain.count_parameters():,}')

# Test decision
x = torch.randn(1, 50, 32)
indicators = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'risk_reward': 2.2, 'atr_pct': 0.3, 'vol_ratio': 1.8, 'momentum': 0.15}

decision = model.make_decision(x, indicators)
print(f'Action: {decision.action}')
print(f'Confidence: {decision.confidence:.2f}')
print(f'Risk Level: {decision.risk_level}')
"
```

- [ ] **Step 4: Commit**

```bash
git add plugins/scalpbot/ai/hybrid/
git commit -m "feat: add Neuro-Symbolic hybrid model"
```

---

## Task 4: AI Forge Interactive Environment

**Covers:** Interactive coding and monitoring environment

**Files:**
- Create: `plugins/scalpbot/ai/forge/ai_forge.py`
- Create: `plugins/scalpbot/ai/forge/monitor.py`
- Create: `plugins/scalpbot/ai/forge/logger.py`

- [ ] **Step 1: Create ai_forge.py**

```python
# plugins/scalpbot/ai/forge/ai_forge.py
"""AI Forge - Interactive Coding & Monitoring Environment."""

import os
import datetime
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


class AIForge:
    """
    Interactive environment for the bot to code, monitor, and explain itself.
    """
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "ai_workspace"
        )
        self.modules_dir = os.path.join(self.workspace, "modules")
        self.logs_dir = os.path.join(self.workspace, "logs")
        self.decisions_dir = os.path.join(self.workspace, "decisions")
        
        self._ensure_dirs()
        self.connect()
    
    def _ensure_dirs(self):
        """Ensure all directories exist."""
        for d in [self.workspace, self.modules_dir, self.logs_dir, self.decisions_dir]:
            os.makedirs(d, exist_ok=True)
    
    def connect(self):
        """Initialize connection."""
        self.log("🔌 [AI FORGE] Sistem bağlandı.")
        self.log(f"🕒 Zaman: {datetime.datetime.now()}")
        self.log(f"📁 Workspace: {self.workspace}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        # Write to log file
        log_file = os.path.join(self.logs_dir, f"forge_{datetime.date.today()}.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    
    def create_module(self, name: str, content: str) -> str:
        """Create a Python module dynamically."""
        filename = f"{name.lower().replace(' ', '_')}.py"
        path = os.path.join(self.modules_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.log(f"✅ Modül oluşturuldu: {filename}")
        return path
    
    def edit_module(self, filename: str, old_str: str, new_str: str) -> bool:
        """Edit an existing module."""
        path = os.path.join(self.modules_dir, filename)
        
        if not os.path.exists(path):
            self.log(f"❌ Dosya bulunamadı: {filename}", "ERROR")
            return False
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = content.replace(old_str, new_str)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.log(f"✏️  Modül düzenlendi: {filename}")
        return True
    
    def log_decision(self, decision: Any, explanation: str):
        """Log a trading decision with explanation."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "decision": str(decision),
            "explanation": explanation
        }
        
        filename = f"decision_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.decisions_dir, filename)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        
        self.log(f"🤖 Karar kaydedildi: {decision}")
    
    def show_status(self) -> Dict:
        """Show current system status."""
        status = {
            "forge_active": True,
            "workspace": self.workspace,
            "modules": len(os.listdir(self.modules_dir)) if os.path.exists(self.modules_dir) else 0,
            "logs_today": self._count_today_logs(),
            "decisions_today": self._count_today_decisions()
        }
        
        self.log("📊 Sistem Durumu:")
        for k, v in status.items():
            self.log(f"   • {k}: {v}")
        
        return status
    
    def _count_today_logs(self) -> int:
        """Count today's log entries."""
        log_file = os.path.join(self.logs_dir, f"forge_{datetime.date.today()}.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                return len(f.readlines())
        return 0
    
    def _count_today_decisions(self) -> int:
        """Count today's decisions."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        count = 0
        for f in os.listdir(self.decisions_dir):
            if f.startswith(f"decision_{today}"):
                count += 1
        return count
```

- [ ] **Step 2: Create monitor.py**

```python
# plugins/scalpbot/ai/forge/monitor.py
"""Real-time monitoring for AI Brain."""

import time
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MetricSnapshot:
    """Single metric snapshot."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class BrainMonitor:
    """Monitor AI Brain performance and decisions."""
    
    def __init__(self):
        self.metrics: List[MetricSnapshot] = []
        self.decisions: List[Dict] = []
        self.start_time = time.time()
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric."""
        snapshot = MetricSnapshot(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics.append(snapshot)
    
    def record_decision(self, decision: Dict):
        """Record a trading decision."""
        decision["timestamp"] = datetime.now().isoformat()
        self.decisions.append(decision)
    
    def get_summary(self) -> Dict:
        """Get monitoring summary."""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "total_metrics": len(self.metrics),
            "total_decisions": len(self.decisions),
            "recent_metrics": [
                {"name": m.name, "value": m.value}
                for m in self.metrics[-10:]
            ],
            "decision_summary": self._summarize_decisions()
        }
    
    def _summarize_decisions(self) -> Dict:
        """Summarize recent decisions."""
        if not self.decisions:
            return {"total": 0}
        
        actions = {}
        for d in self.decisions[-100:]:
            action = d.get("action", "UNKNOWN")
            actions[action] = actions.get(action, 0) + 1
        
        return {
            "total": len(self.decisions),
            "actions": actions,
            "avg_confidence": sum(d.get("confidence", 0) for d in self.decisions) / len(self.decisions)
        }
    
    def display_dashboard(self):
        """Display live dashboard."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("🧠 METABRAIN MONITOR DASHBOARD")
        print("=" * 60)
        print(f"⏱️  Uptime: {summary['uptime_seconds']:.0f}s")
        print(f"📊 Metrics: {summary['total_metrics']}")
        print(f"🤖 Decisions: {summary['total_decisions']}")
        
        if summary['decision_summary'].get('actions'):
            print("\n📈 Decision Distribution:")
            for action, count in summary['decision_summary']['actions'].items():
                print(f"   {action}: {count}")
        
        if summary['decision_summary'].get('avg_confidence'):
            print(f"\n🎯 Avg Confidence: {summary['decision_summary']['avg_confidence']:.1%}")
        
        print("=" * 60)
```

- [ ] **Step 3: Create logger.py**

```python
# plugins/scalpbot/ai/forge/logger.py
"""Structured logging for AI decisions."""

import json
import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class DecisionLogger:
    """Log decisions with full context."""
    
    def __init__(self, log_dir: str = "logs/decisions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, decision_type: str, data: Dict[str, Any], 
            explanation: str = "") -> str:
        """Log a decision."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": decision_type,
            "data": data,
            "explanation": explanation
        }
        
        filename = f"{decision_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def log_signal(self, symbol: str, action: str, confidence: float,
                   indicators: Dict, neural_output: Dict = None,
                   symbolic_output: Dict = None):
        """Log a trading signal."""
        data = {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "indicators": indicators,
            "neural": neural_output,
            "symbolic": symbolic_output
        }
        
        explanation = f"Signal: {action} {symbol} @ {confidence:.1%}"
        return self.log("signal", data, explanation)
    
    def log_risk_check(self, passed: bool, rules_checked: int,
                      rules_passed: int, risk_level: str):
        """Log a risk check."""
        data = {
            "passed": passed,
            "rules_checked": rules_checked,
            "rules_passed": rules_passed,
            "risk_level": risk_level
        }
        
        explanation = f"Risk check: {'PASSED' if passed else 'FAILED'} ({rules_passed}/{rules_checked})"
        return self.log("risk_check", data, explanation)
```

- [ ] **Step 4: Create forge __init__.py**

```python
# plugins/scalpbot/ai/forge/__init__.py
"""AI Forge modules."""

from .ai_forge import AIForge
from .monitor import BrainMonitor
from .logger import DecisionLogger

__all__ = ["AIForge", "BrainMonitor", "DecisionLogger"]
```

- [ ] **Step 5: Test forge modules**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
PYTHONPATH=. python -c "
from plugins.scalpbot.ai.forge.ai_forge import AIForge
from plugins.scalpbot.ai.forge.monitor import BrainMonitor
from plugins.scalpbot.ai.forge.logger import DecisionLogger

# Test forge
forge = AIForge(workspace='/tmp/ai_test')
forge.show_status()

# Test monitor
monitor = BrainMonitor()
monitor.record_metric('confidence', 0.85)
monitor.record_decision({'action': 'LONG', 'confidence': 0.85})
monitor.display_dashboard()

# Test logger
logger = DecisionLogger(log_dir='/tmp/ai_test/logs')
path = logger.log_signal('BTC-USDT', 'LONG', 0.85, {'rsi': 45})
print(f'Logged to: {path}')
"
```

- [ ] **Step 6: Commit**

```bash
git add plugins/scalpbot/ai/forge/
git commit -m "feat: add AI Forge interactive environment"
```

---

## Task 5: Integrate All Systems into MetaBrain

**Covers:** Connect all AI components

**Files:**
- Modify: `plugins/scalpbot/ai/brain.py`

- [ ] **Step 1: Update brain.py with all new components**

```python
# Add imports to brain.py
from .neural.scalp_brain import ScalpBrain
from .hybrid.neuro_symbolic import NeuroSymbolicTrader
from .symbolic.rule_engine import SymbolicRuleEngine
from .symbolic.fuzzy_logic import FuzzyTradingSystem
from .forge.ai_forge import AIForge
from .forge.monitor import BrainMonitor
from .forge.logger import DecisionLogger
```

- [ ] **Step 2: Update MetaBrain class**

Add to MetaBrain.__init__:
```python
# Neuro-Symbolic
self.hybrid_model = NeuroSymbolicTrader(input_dim=32, hidden_dim=128)
self.symbolic_engine = SymbolicRuleEngine()
self.fuzzy_system = FuzzyTradingSystem()

# AI Forge
self.forge = AIForge()
self.monitor = BrainMonitor()
self.logger = DecisionLogger()
```

- [ ] **Step 3: Update predict method to use hybrid**

```python
def predict(self, df, indicators, patterns, news=None, fear_greed_value=50):
    """Enhanced predict with Neuro-Symbolic."""
    # ... existing code ...
    
    # Neuro-Symbolic decision
    import torch
    features = self.feature_engine.extract_all(df, indicators, patterns)
    x = torch.FloatTensor(features.price_features[:32]).unsqueeze(0).unsqueeze(0)
    
    hybrid_decision = self.hybrid_model.make_decision(x, indicators)
    
    # Log decision
    self.monitor.record_decision({
        "action": hybrid_decision.action,
        "confidence": hybrid_decision.confidence,
        "risk_level": hybrid_decision.risk_level
    })
    
    self.logger.log_signal(
        symbol=df.index[-1],
        action=hybrid_decision.action,
        confidence=hybrid_decision.confidence,
        indicators=indicators,
        neural_output={"lstm": lstm_output, "transformer": transformer_output},
        symbolic_output={"rules": len(hybrid_decision.explanation.split(chr(10)))}
    )
    
    return BrainOutput(
        direction=hybrid_decision.action,
        confidence=hybrid_decision.confidence,
        prediction=meta_prediction,
        lstm_output=lstm_output,
        transformer_output=transformer_output,
        rl_output=rl_output,
        sentiment_output=sentiment_output,
        processing_time=processing_time
    )
```

- [ ] **Step 4: Test full integration**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
PYTHONPATH=. python -c "
from plugins.scalpbot.ai.brain import MetaBrain
import pandas as pd
import numpy as np

brain = MetaBrain()
brain.forge.log('🚀 MetaBrain with Neuro-Symbolic initialized!')

dates = pd.date_range('2024-01-01', periods=100, freq='1h')
df = pd.DataFrame({
    'open': np.random.uniform(50000, 60000, 100),
    'high': np.random.uniform(50000, 60000, 100),
    'low': np.random.uniform(50000, 60000, 100),
    'close': np.random.uniform(50000, 60000, 100),
    'volume': np.random.uniform(1e9, 5e9, 100)
}, index=dates)

indicators = {
    'rsi': 45, 'ema_score': 28, 'volume_score': 22,
    'risk_reward': 2.2, 'atr_pct': 0.3, 'vol_ratio': 1.8, 'momentum': 0.15
}

output = brain.predict(df, indicators, ['STRONG_BULLISH'])
print(f'Direction: {output.direction}')
print(f'Confidence: {output.confidence:.2f}')
brain.monitor.display_dashboard()
"
```

- [ ] **Step 5: Commit**

```bash
git add plugins/scalpbot/ai/brain.py
git commit -m "feat: integrate Neuro-Symbolic and AI Forge into MetaBrain"
```

---

## Task 6: Update AI __init__.py

**Covers:** Proper module exports

**Files:**
- Modify: `plugins/scalpbot/ai/__init__.py`

- [ ] **Step 1: Update __init__.py**

```python
# plugins/scalpbot/ai/__init__.py
"""AI Brain modules for ScalpBot."""

try:
    from .brain import MetaBrain
except ImportError:
    MetaBrain = None

try:
    from .neural.scalp_brain import ScalpBrain
except ImportError:
    ScalpBrain = None

try:
    from .hybrid.neuro_symbolic import NeuroSymbolicTrader
except ImportError:
    NeuroSymbolicTrader = None

try:
    from .symbolic.rule_engine import SymbolicRuleEngine
except ImportError:
    SymbolicRuleEngine = None

try:
    from .forge.ai_forge import AIForge
except ImportError:
    AIForge = None

__all__ = [
    "MetaBrain", "ScalpBrain", "NeuroSymbolicTrader",
    "SymbolicRuleEngine", "AIForge"
]
```

- [ ] **Step 2: Commit**

```bash
git add plugins/scalpbot/ai/__init__.py
git commit -m "feat: update AI module exports"
```

---

## Task 7: Integration Tests

**Covers:** Test all new components

**Files:**
- Create: `tests/test_neurosymbolic.py`

- [ ] **Step 1: Create comprehensive test file**

```python
# tests/test_neurosymbolic.py
"""Tests for Neuro-Symbolic AI components."""

import pytest
import torch
import numpy as np
import pandas as pd
from plugins.scalpbot.ai.neural.scalp_brain import ScalpBrain
from plugins.scalpbot.ai.symbolic.rule_engine import SymbolicRuleEngine
from plugins.scalpbot.ai.symbolic.fuzzy_logic import FuzzyTradingSystem
from plugins.scalpbot.ai.hybrid.neuro_symbolic import NeuroSymbolicTrader
from plugins.scalpbot.ai.forge.ai_forge import AIForge
from plugins.scalpbot.ai.forge.monitor import BrainMonitor


def test_scalp_brain():
    """Test ScalpBrain deep architecture."""
    model = ScalpBrain(input_dim=32, hidden_dim=64, num_lstm_layers=1, num_transformer_layers=1)
    x = torch.randn(2, 50, 32)
    output = model(x)
    assert output.meta_prediction.shape == (2, 3)
    assert output.actor_logits.shape == (2, 3)
    assert output.critic_value.shape == (2, 1)
    assert model.count_parameters() > 0


def test_symbolic_rule_engine():
    """Test symbolic rule engine."""
    engine = SymbolicRuleEngine()
    context = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'risk_reward': 2.2, 'atr_pct': 0.3}
    decision = engine.evaluate(context)
    assert decision.action in ["LONG", "SHORT", "HOLD"]
    assert 0 <= decision.confidence <= 1


def test_fuzzy_logic():
    """Test fuzzy logic system."""
    fuzzy = FuzzyTradingSystem()
    action, conf = fuzzy.evaluate(rsi=45, volume_ratio=1.8, momentum=0.15)
    assert action in ["strong_buy", "buy", "hold", "sell", "strong_sell"]
    assert 0 <= conf <= 1


def test_neuro_symbolic():
    """Test hybrid neuro-symbolic model."""
    model = NeuroSymbolicTrader(input_dim=32, hidden_dim=64)
    x = torch.randn(1, 50, 32)
    indicators = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'vol_ratio': 1.8, 'momentum': 0.15}
    decision = model.make_decision(x, indicators)
    assert decision.action in ["LONG", "SHORT", "HOLD"]
    assert 0 <= decision.confidence <= 1


def test_ai_forge():
    """Test AI Forge environment."""
    forge = AIForge(workspace='/tmp/forge_test')
    status = forge.show_status()
    assert status['forge_active'] is True
    
    path = forge.create_module('test_module', 'x = 1')
    assert os.path.exists(path)


def test_brain_monitor():
    """Test brain monitor."""
    monitor = BrainMonitor()
    monitor.record_metric('confidence', 0.85)
    monitor.record_decision({'action': 'LONG', 'confidence': 0.85})
    summary = monitor.get_summary()
    assert summary['total_metrics'] == 1
    assert summary['total_decisions'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run tests**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -m pytest tests/test_neurosymbolic.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_neurosymbolic.py
git commit -m "test: add Neuro-Symbolic integration tests"
```

---

## Execution Handoff

After completing all tasks:

1. Run all tests to verify components work
2. Test MetaBrain end-to-end
3. Verify AI Forge logging works

**Architecture Summary:**
```
🧠 ScalpBrain (Neural)
├── CNN Feature Extractor (Sensory Cortex)
├── Stacked LSTM (Hippocampus)
├── Transformer Encoder (Association Areas)
├── Multi-Head Attention
├── Meta Output Head
└── Actor-Critic Heads (Prefrontal Cortex)

⚖️ Symbolic Engine
├── Rule Engine (If-Then rules)
├── Knowledge Base (Financial ontology)
└── Fuzzy Logic (Bulanık mantık)

🔗 Hybrid Fusion
├── Neuro-Symbolic Trader
└── Confidence Calibration

🔧 AI Forge
├── Interactive Environment
├── Real-time Monitor
└── Decision Logger
```