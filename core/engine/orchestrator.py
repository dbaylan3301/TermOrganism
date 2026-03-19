from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from core.engine.ranker import CandidateRanker
from core.engine.router import PolicyRouter
from core.experts.base import RepairExpert
from core.memory.event_store import EventStore
from core.models.schemas import FailureContext, RankedCandidate
from core.util.fingerprints import error_fingerprint
from core.verify.sandbox import VerifierHub


class Orchestrator:
    def __init__(
        self,
        *,
        router: PolicyRouter,
        experts: list[RepairExpert],
        verifier: VerifierHub,
        ranker: CandidateRanker,
        store: EventStore,
    ):
        self.router = router
        self.experts = {e.name: e for e in experts}
        self.verifier = verifier
        self.ranker = ranker
        self.store = store

    def run(self, ctx: FailureContext) -> RankedCandidate | None:
        routes = self.router.route(ctx, list(self.experts.values()), top_k=3)
        evaluated = []

        for route in routes:
            expert = self.experts[route.expert_name]
            for candidate in expert.propose(ctx):
                candidate.router_score = route.score
                verification = self.verifier.verify(ctx, candidate)
                evaluated.append((candidate, verification))

        winner = self.ranker.select(evaluated)
        self._record(ctx, routes, evaluated, winner)
        return winner

    def _record(self, ctx, routes, evaluated, winner):
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "file_path": ctx.file_path,
            "language": ctx.language,
            "exception_type": ctx.exception_type,
            "error_fingerprint": error_fingerprint(ctx.stderr, ctx.exception_type),
            "routes": [asdict(item) for item in routes],
            "candidates": [
                {
                    "candidate": asdict(candidate),
                    "verification": asdict(verification),
                }
                for candidate, verification in evaluated
            ],
            "winning_expert": winner.candidate.expert_name if winner else None,
            "ok": bool(winner),
            "patched_code": winner.candidate.patched_code if winner else None,
            "diff": winner.candidate.patch_unified_diff if winner else None,
            "winner_score": winner.final_score if winner else 0.0,
        }
        self.store.append(event)
