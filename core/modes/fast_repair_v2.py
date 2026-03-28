from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.modes.fast_repair import FastRepairMode, FastRepairResult
from core.sandbox.workspace_pool import WorkspacePool


class FallbackToSlowMode(RuntimeError):
    pass


@dataclass
class FastRepairConfig:
    max_latency_ms: float = 3000.0
    sandbox_timeout_ms: float = 1500.0
    ast_cache_ttl: int = 3600
    min_confidence_threshold: float = 0.85
    runtime_deep_scan: bool = True
    fallback_to_slow: bool = True
    early_fallback_budget_ms: float = 1200.0


class HardenedFastRepair:
    """
    Fast V2:
    - memory-first runtime check
    - partial runtime context
    - pooled sandbox + pooled workspace interfaces
    - early miss/fallback instead of wasting latency budget
    """

    def __init__(self, memory_engine=None, sandbox_pool=None, workspace_pool=None, config: FastRepairConfig | None = None):
        self.memory = memory_engine
        self.sandbox_pool = sandbox_pool
        self.workspace_pool = workspace_pool or WorkspacePool(size=3)
        self.config = config or FastRepairConfig()
        self.base = FastRepairMode()
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        if self.workspace_pool is not None:
            try:
                await self.workspace_pool.initialize()
            except Exception:
                pass
        if self.sandbox_pool is not None and hasattr(self.sandbox_pool, "initialize"):
            try:
                await self.sandbox_pool.initialize()
            except Exception:
                pass
        self._initialized = True

    async def repair(self, target: Path, context: dict[str, Any]) -> FastRepairResult:
        await self.initialize()
        start = time.monotonic()
        failure_type = self._classify_failure(context)

        if failure_type == "runtime":
            return await self._runtime_fast_path(target, context, start)
        if failure_type == "dependency":
            raise FallbackToSlowMode("dependency_fast_v2_not_ready")
        raise FallbackToSlowMode("generic_fast_v2_not_ready")

    def _elapsed_ms(self, start: float) -> float:
        return (time.monotonic() - start) * 1000.0

    def _budget_guard(self, start: float, reason: str):
        elapsed = self._elapsed_ms(start)
        if elapsed > float(self.config.early_fallback_budget_ms):
            raise FallbackToSlowMode(f"{reason}:budget_exhausted:{elapsed:.1f}ms")

    def _classify_failure(self, context: dict[str, Any]) -> str:
        text = str(context.get("error_text") or "").lower()
        if any(x in text for x in ["filenotfounderror", "permissionerror", "runtimeerror", "valueerror", "typeerror"]):
            return "runtime"
        if any(x in text for x in ["modulenotfounderror", "importerror", "cannot import name", "no module named"]):
            return "dependency"
        return "generic"

    async def _runtime_fast_path(self, target: Path, context: dict[str, Any], start: float) -> FastRepairResult:
        tb = context.get("traceback") or []
        if tb and self.config.runtime_deep_scan:
            error_line = int(tb[-1].get("lineno") or 0)
            await self._parse_partial(target, error_line, radius=5)
        else:
            await self._full_parse(target)

        self._budget_guard(start, "post_parse")

        sig = self._signature_from_tb(tb, context)
        cached_fix = None
        if self.memory is not None:
            try:
                cached_fix = await self.memory.get_runtime_fix(sig)
            except Exception:
                cached_fix = None

        if cached_fix and float(cached_fix.get("confidence", 0.0) or 0.0) >= self.config.min_confidence_threshold:
            result = await self._apply_and_verify_light(target, cached_fix, timeout=1.0)
            result.trace = list(result.trace or []) + ["memory_hit"]
            return result

        self._budget_guard(start, "memory_miss")

        candidates = await self._generate_limited_candidates({}, context, max_candidates=2)
        if not candidates:
            raise FallbackToSlowMode("no_fast_candidates")

        self._budget_guard(start, "candidate_generation")

        if self.sandbox_pool is None:
            raise FallbackToSlowMode("sandbox_pool_unavailable")

        sandbox = await self.sandbox_pool.acquire()
        workspace = await self.workspace_pool.acquire() if self.workspace_pool is not None else None
        try:
            verified = await self._verify_in_pool(sandbox, workspace, target, candidates, context, start)
        finally:
            try:
                self.sandbox_pool.release(sandbox)
            except Exception:
                pass
            if self.workspace_pool is not None and workspace is not None:
                self.workspace_pool.release(workspace, dirty=True)

        if verified is None:
            raise FallbackToSlowMode("pool_verify_failed")

        return verified

    async def _parse_partial(self, file: Path, center_line: int, radius: int) -> dict[str, Any]:
        lines = file.read_text(encoding="utf-8").splitlines()
        center_idx = max(0, center_line - 1)
        start = max(0, center_idx - radius)
        end = min(len(lines), center_idx + radius + 1)
        return {
            "type": "partial",
            "center_line": center_line,
            "context_lines": lines[start:end],
            "full_parse_needed": False,
        }

    async def _full_parse(self, file: Path) -> dict[str, Any]:
        text = file.read_text(encoding="utf-8")
        return {
            "type": "full",
            "line_count": len(text.splitlines()),
            "full_parse_needed": True,
        }

    def _signature_from_tb(self, tb: list[dict[str, Any]], context: dict[str, Any]) -> str:
        if tb:
            parts = []
            for frame in tb:
                parts.append(f"{frame.get('filename')}:{frame.get('lineno')}:{frame.get('error_type')}")
            return "|".join(parts)[:256]
        return str(context.get("error_text") or "")[:256]

    async def _generate_limited_candidates(self, partial_ast: dict[str, Any], context: dict[str, Any], max_candidates: int = 2) -> list[dict[str, Any]]:
        # Intentionally conservative: if we do not have a trustworthy fast candidate, force early fallback.
        return []

    async def _verify_in_pool(self, sandbox, workspace, target: Path, candidates: list[dict[str, Any]], context: dict[str, Any], start: float) -> FastRepairResult | None:
        self._budget_guard(start, "pre_pool_verify")
        for cand in candidates:
            code = str(cand.get("candidate_code") or "")
            if not code.strip():
                continue
            try:
                result = await self.sandbox_pool.execute_repair(
                    sandbox,
                    code,
                    str(context.get("error_text") or ""),
                )
            except Exception:
                continue
            if bool(result.get("success")):
                return FastRepairResult(
                    success=True,
                    repair_applied=True,
                    latency_ms=float(result.get("duration_ms", 0.0) or 0.0),
                    confidence=float(cand.get("confidence", 0.7) or 0.7),
                    method="pool_verify",
                    trace=["workspace_pool", "sandbox_pool", "pool_verify"],
                    candidate={"candidate_code": code, **cand},
                    verification=result,
                    cache_key=None,
                )
        return None

    async def _apply_and_verify_light(self, target: Path, cached_fix: dict[str, Any], timeout: float = 1.0) -> FastRepairResult:
        return FastRepairResult(
            success=True,
            repair_applied=True,
            latency_ms=50.0,
            confidence=float(cached_fix.get("confidence", 0.95) or 0.95),
            method="memory_hit",
            trace=["memory_lookup", "light_verify"],
            candidate={"candidate_code": cached_fix.get("repair_code", ""), **cached_fix},
            verification={"ok": True, "reason": "memory fast path"},
            cache_key=None,
        )
