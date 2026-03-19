from __future__ import annotations

from core.models.schemas import RankedCandidate, RepairCandidate, VerificationResult


class CandidateRanker:
    def rank(self, candidate: RepairCandidate, verification: VerificationResult) -> float:
        return (
            0.30 * candidate.router_score
            + 0.20 * candidate.expert_score
            + 0.30 * verification.score
            + 0.10 * candidate.memory_prior
            + 0.10 * candidate.patch_safety_score
        )

    def select(self, candidates: list[tuple[RepairCandidate, VerificationResult]]) -> RankedCandidate | None:
        ranked: list[RankedCandidate] = []
        for candidate, verification in candidates:
            if not verification.ok:
                continue
            ranked.append(
                RankedCandidate(
                    candidate=candidate,
                    verification=verification,
                    final_score=self.rank(candidate, verification),
                )
            )
        if not ranked:
            return None
        ranked.sort(key=lambda item: item.final_score, reverse=True)
        return ranked[0]
