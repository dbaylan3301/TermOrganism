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
