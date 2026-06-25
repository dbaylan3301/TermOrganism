from __future__ import annotations

"""Backward-compatible shim — all logic moved to core.repair."""
from core.repair import (
    repair,
    build_candidates,
    build_and_rank_plans,
    verify_repair,
    boost_confidence,
    attach_hot_cache_boost,
    apply_hot_cache_to_payload,
    force_plan_target_to_file,
    resolve_semantic_target,
    infer_provider_from_imports,
    build_semantic_prelude,
    emit_thought,
    EventStoreAdapter,
)

__all__ = [
    "repair",
    "build_candidates",
    "build_and_rank_plans",
    "verify_repair",
    "boost_confidence",
    "attach_hot_cache_boost",
    "apply_hot_cache_to_payload",
    "force_plan_target_to_file",
    "resolve_semantic_target",
    "infer_provider_from_imports",
    "build_semantic_prelude",
    "emit_thought",
    "EventStoreAdapter",
]
