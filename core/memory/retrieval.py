from __future__ import annotations

from core.models.schemas import FailureContext
from core.util.fingerprints import error_fingerprint


class RetrievalIndex:
    def __init__(self, events: list[dict]):
        self.events = events

    def lookup(self, ctx: FailureContext) -> list[dict]:
        fp = error_fingerprint(ctx.stderr, ctx.exception_type)
        matches = []
        for event in self.events:
            similarity = 0.0
            if event.get("error_fingerprint") == fp:
                similarity += 0.9
            if event.get("language") == ctx.language:
                similarity += 0.1
            if event.get("exception_type") == ctx.exception_type:
                similarity += 0.1
            if similarity > 0:
                row = dict(event)
                row["similarity"] = min(similarity, 1.0)
                matches.append(row)
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches
