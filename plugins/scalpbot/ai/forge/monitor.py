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
        print("METABRAIN MONITOR DASHBOARD")
        print("=" * 60)
        print(f"  Uptime: {summary['uptime_seconds']:.0f}s")
        print(f"  Metrics: {summary['total_metrics']}")
        print(f"  Decisions: {summary['total_decisions']}")

        if summary['decision_summary'].get('actions'):
            print("\n  Decision Distribution:")
            for action, count in summary['decision_summary']['actions'].items():
                print(f"   {action}: {count}")

        if summary['decision_summary'].get('avg_confidence'):
            print(f"\n  Avg Confidence: {summary['decision_summary']['avg_confidence']:.1%}")

        print("=" * 60)
