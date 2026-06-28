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
