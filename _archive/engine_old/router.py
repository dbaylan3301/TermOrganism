from __future__ import annotations

from core.experts.base import RepairExpert
from core.models.schemas import FailureContext, RoutingDecision


class PolicyRouter:
    def route(self, ctx: FailureContext, experts: list[RepairExpert], top_k: int = 3) -> list[RoutingDecision]:
        decisions: list[RoutingDecision] = []
        for expert in experts:
            score, reasons = expert.score(ctx)
            if score <= 0:
                continue
            decisions.append(RoutingDecision(expert_name=expert.name, score=score, reasons=reasons))
        decisions.sort(key=lambda item: item.score, reverse=True)
        return decisions[:top_k]
