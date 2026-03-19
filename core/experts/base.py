from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.schemas import FailureContext, RepairCandidate


class RepairExpert(ABC):
    name: str = "base"
    supported_languages: set[str] = set()

    @abstractmethod
    def score(self, ctx: FailureContext) -> tuple[float, list[str]]:
        raise NotImplementedError

    @abstractmethod
    def propose(self, ctx: FailureContext) -> list[RepairCandidate]:
        raise NotImplementedError
