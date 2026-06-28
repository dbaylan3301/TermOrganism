# plugins/scalpbot/ai/hybrid/neuro_symbolic.py
"""Neuro-Symbolic Hybrid Model."""

import torch
import torch.nn as nn
import numpy as np
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
            nn.Linear(9, 16),
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
        # Set to eval mode to avoid BatchNorm issues
        self.eval()
        
        with torch.no_grad():
            fused_action, confidence = self.forward(market_data, indicators)

            # Get action
            action_probs = torch.softmax(fused_action, dim=-1)
            action_idx = torch.argmax(action_probs).item()
            actions = ["LONG", "SHORT", "HOLD"]
            action = actions[action_idx]

            # Get symbolic decision for explanation
            try:
                # Convert any array values to scalars for rule engine
                clean_indicators = {}
                for k, v in indicators.items():
                    if isinstance(v, (list, np.ndarray)):
                        clean_indicators[k] = float(v[-1]) if len(v) > 0 else 0.0
                    else:
                        clean_indicators[k] = v
                symbolic_decision = self.symbolic_engine.evaluate(clean_indicators)
            except Exception:
                # Fallback symbolic decision
                from ..symbolic.rule_engine import SymbolicDecision, RuleResult
                symbolic_decision = SymbolicDecision(
                    action="HOLD", confidence=0.5, position_size_modifier=1.0,
                    rules_triggered=[], explanation="Fallback", risk_level="MEDIUM"
                )

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
            f"\U0001f9e0 Neuro-Symbolic Decision: {action}",
            f"\U0001f4ca Confidence: {confidence:.1%}",
            f"\u2696\ufe0f Position Size: {symbolic.position_size_modifier:.0%}",
            f"\U0001f3af Risk Level: {symbolic.risk_level}",
            "",
            "Neural Analysis:",
            f"  \u2022 Pattern recognition: Active",
            f"  \u2022 Temporal memory: Engaged",
            "",
            "Symbolic Reasoning:",
        ]

        for rule in symbolic.rules_triggered[:5]:
            if rule.triggered:
                lines.append(f"  \u2713 {rule.explanation}")

        return "\n".join(lines)
