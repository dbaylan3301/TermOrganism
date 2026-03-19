from __future__ import annotations

from core.experts.base import RepairExpert
from core.memory.retrieval import RetrievalIndex
from core.models.schemas import FailureContext, RepairCandidate


class MemoryRetrievalExpert(RepairExpert):
    name = "memory_retrieval"
    supported_languages = {"python", "shell"}

    def __init__(self, retrieval: RetrievalIndex):
        self.retrieval = retrieval

    def score(self, ctx: FailureContext) -> tuple[float, list[str]]:
        matches = self.retrieval.lookup(ctx)
        if not matches:
            return 0.0, []
        top = matches[0]
        score = min(0.85, 0.30 +
