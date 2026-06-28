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
