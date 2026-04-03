from __future__ import annotations

from typing import Any

from .synaptic_engine import SynapticMemory


def remember_from_result(
    *,
    result: dict[str, Any],
    signature: str,
    route: str,
    file_path: str | None = None,
    repo_type: str | None = None,
    intent: str = "repair",
) -> dict[str, Any]:
    memory = SynapticMemory()
    success = bool(result.get("success"))
    verify_ok = None
    if isinstance(result.get("verify"), dict):
        verify_ok = result["verify"].get("ok")

    confidence = 0.0
    if isinstance(result.get("confidence"), dict):
        confidence = float(result["confidence"].get("score", 0.0) or 0.0)

    return memory.remember_repair_outcome(
        signature=signature,
        route=route,
        success=success,
        file_path=file_path or result.get("target_file"),
        repo_type=repo_type,
        intent=intent,
        confidence=confidence,
        verify_ok=verify_ok,
        test_ok=None,
        latency_ms=result.get("latency_ms"),
    )
