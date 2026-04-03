from __future__ import annotations

from typing import Any

from .synaptic_engine import SynapticMemory


def choose_route_with_prior(
    *,
    signature: str,
    repo_type: str | None = None,
    file_path: str | None = None,
    intent: str | None = "repair",
    fallback_route: str = "fast",
    threshold: float = 0.62,
) -> dict[str, Any]:
    memory = SynapticMemory()
    ranked = memory.rank_routes(
        signature=signature,
        repo_type=repo_type,
        file_path=file_path,
        intent=intent,
    )

    top = ranked[0] if ranked else None
    if top and top["matched"] and top["prior"] >= threshold:
        return {
            "route": top["route"],
            "used_synaptic_prior": True,
            "prior": top["prior"],
            "seen_total": top["seen_total"],
            "evidence": top["evidence"],
            "fallback_route": fallback_route,
        }

    return {
        "route": fallback_route,
        "used_synaptic_prior": False,
        "prior": top["prior"] if top else 0.50,
        "seen_total": top["seen_total"] if top else 0,
        "evidence": top["evidence"] if top else {},
        "fallback_route": fallback_route,
    }
