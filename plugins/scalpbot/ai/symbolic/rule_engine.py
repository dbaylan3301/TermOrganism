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
    priority: RulePriority = RulePriority.LOW


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
                explanation=f"{'✓' if triggered else '✗'} {rule.description}",
                priority=rule.priority
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
