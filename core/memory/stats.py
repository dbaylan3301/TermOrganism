from __future__ import annotations

from collections import Counter


class MemoryStats:
    def __init__(self, events: list[dict]):
        self.events = events

    def expert_success_rates(self) -> dict[str, float]:
        totals = Counter()
        wins = Counter()
        for e in self.events:
            expert = e.get("winning_expert")
            if not expert:
                continue
            totals[expert] += 1
            if e.get("ok"):
                wins[expert] += 1
        return {k: wins[k] / totals[k] for k in totals}
