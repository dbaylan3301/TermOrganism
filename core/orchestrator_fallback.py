from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable

RunHotForce = Callable[[Path, dict[str, Any]], Awaitable[dict[str, Any]]]
RunPipeline = Callable[[Path, str, dict[str, Any]], Awaitable[dict[str, Any]]]
ShouldHotForce = Callable[[dict[str, Any]], bool]


class FallbackOrchestrator:
    """
    Safe chain:
    hot_force -> fast -> normal
    """

    def __init__(
        self,
        run_hot_force: RunHotForce,
        run_existing_pipeline: RunPipeline,
        should_hot_force: ShouldHotForce,
    ):
        self.run_hot_force = run_hot_force
        self.run_existing_pipeline = run_existing_pipeline
        self.should_hot_force = should_hot_force

    async def repair(self, file_path: Path, context: dict[str, Any], mode: str = "auto") -> dict[str, Any]:
        stage_errors: list[dict[str, Any]] = []

        if mode == "normal":
            result = await self._try_stage("normal", file_path, context, stage_errors)
            return self._annotate(result, ["normal"], stage_errors)

        if mode == "fast":
            result = await self._try_stage("fast", file_path, context, stage_errors)
            if self._is_success(result):
                return self._annotate(result, ["fast"], stage_errors)

            result2 = await self._try_stage("normal", file_path, context, stage_errors)
            if self._is_success(result2):
                return self._annotate(result2, ["fast_failed", "normal"], stage_errors)

            return self._annotate(result2, ["fast_failed", "normal_failed"], stage_errors)

        # auto + hot_force explicit
        should_try_hot = (mode == "hot_force") or self.should_hot_force(context)

        if should_try_hot:
            hot = await self._try_stage("hot_force", file_path, context, stage_errors)
            if self._is_success(hot):
                return self._annotate(hot, ["hot_force"], stage_errors)

        fast = await self._try_stage("fast", file_path, context, stage_errors)
        if self._is_success(fast):
            chain = ["hot_force_failed", "fast"] if should_try_hot else ["fast"]
            return self._annotate(fast, chain, stage_errors)

        normal = await self._try_stage("normal", file_path, context, stage_errors)
        if self._is_success(normal):
            chain = ["hot_force_failed", "fast_failed", "normal"] if should_try_hot else ["fast_failed", "normal"]
            return self._annotate(normal, chain, stage_errors)

        chain = ["hot_force_failed", "fast_failed", "normal_failed"] if should_try_hot else ["fast_failed", "normal_failed"]
        return self._annotate(normal, chain, stage_errors)

    async def _try_stage(
        self,
        stage: str,
        file_path: Path,
        context: dict[str, Any],
        stage_errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            if stage == "hot_force":
                result = await asyncio.wait_for(self.run_hot_force(file_path, context), timeout=1.5)
            elif stage == "fast":
                result = await asyncio.wait_for(self.run_existing_pipeline(file_path, "fast", context), timeout=10.0)
            elif stage == "normal":
                result = await asyncio.wait_for(self.run_existing_pipeline(file_path, "normal", context), timeout=45.0)
            else:
                result = {"success": False, "error": f"unknown stage: {stage}"}
        except Exception as exc:
            result = {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        if not self._is_success(result):
            stage_errors.append({
                "stage": stage,
                "error": self._extract_error(result),
            })
        return result

    def _is_success(self, result: dict[str, Any] | None) -> bool:
        if not isinstance(result, dict):
            return False
        if bool(result.get("success")):
            return True

        for key in ("verify", "branch_result", "contract_result", "behavioral_verify"):
            value = result.get(key)
            if isinstance(value, dict) and bool(value.get("ok")):
                return True

        return False

    def _extract_error(self, result: dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "unknown_failure"
        if result.get("error"):
            return str(result.get("error"))
        verify = result.get("verify") or {}
        if isinstance(verify, dict) and verify.get("reason"):
            return str(verify.get("reason"))
        return "stage_failed"

    def _annotate(self, result: dict[str, Any], chain: list[str], stage_errors: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(result, dict):
            result = {"success": False, "error": "invalid_result"}
        result["fallback_chain"] = chain
        if stage_errors:
            result["stage_errors"] = stage_errors
        return result
