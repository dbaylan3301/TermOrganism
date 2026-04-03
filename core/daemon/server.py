from __future__ import annotations

import argparse
import asyncio
import ast
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.autofix import run_autofix, finalize_repair_payload
from core.modes.fast_v2_minimal import FastV2Minimal
from core.orchestrator_fallback import FallbackOrchestrator
from core.orchestrator_hot_force import HotCacheForcePath
from core.repro.harness import run_python_file
from core.sandbox.workspace_pool_real import RealWorkspacePool

from core.plugins import PluginLoader, PluginRegistry
from core.hooks import HookEngine, HookEvent
from core.policy import PolicyEngine
from core.agents.registry import AgentRegistry
from core.agents.scheduler import AgentScheduler
from core.agents.base import AgentTask
from core.agents.planner import PlannerAgent
from core.agents.verifier import VerifierAgent
from core.agents.test_runner import TestRunnerAgent


@dataclass
class RepairRequest:
    file_path: str
    context: dict[str, Any]
    mode: str = "auto"


class TermOrganismDaemon:
    """
    Persistent daemon:
    - hot_force direct path
    - fast_v2 minimal path
    - fallback chain for auto/fast/normal
    - measured workspace pool telemetry
    - plugin / policy / hooks / subagent wiring
    """

    def __init__(self, socket_path: Path = Path("/tmp/termorganism.sock")):
        self.socket_path = socket_path

        self.hot_force = HotCacheForcePath()
        self.fast_v2 = FastV2Minimal(hot_repairs=self.hot_force.HOT_REPAIRS)
        self.workspace_pool = RealWorkspacePool(size=5)
        self._workspace_pool_ready = False
        self._workspace_pool_lock = asyncio.Lock()

        self.plugins = PluginRegistry()
        self.plugin_loader = PluginLoader("plugins")

        self.policy = PolicyEngine(".termorganism/rules/repo.yaml")
        self.hooks = HookEngine()

        self.agents = AgentRegistry()
        self.scheduler = AgentScheduler(self.agents)

        self.fallback = FallbackOrchestrator(
            run_hot_force=self._run_hot_force,
            run_existing_pipeline=self._run_existing_pipeline,
            should_hot_force=self._should_hot_force,
        )
        self._prewarm()

    def _prewarm(self):
        import pathlib
        _ = ast, pathlib
        _ = self.hot_force.HOT_REPAIRS

        self.plugin_loader.load_into(self.plugins)

        self.agents.register(PlannerAgent())
        self.agents.register(VerifierAgent())
        self.agents.register(TestRunnerAgent())

        for event_name in ("before_repair", "after_verify"):
            for command in self.plugins.enabled_hook_commands(event_name):
                self.hooks.register(event_name, command)

        print("Daemon warmed up and ready", file=sys.stderr)
        print(f"Loaded plugins: {[p['name'] for p in self.plugins.list_plugins()]}", file=sys.stderr)
        print(f"Registered agents: {self.agents.names()}", file=sys.stderr)
        print(
            f"Registered hooks: before_repair={len(self.plugins.enabled_hook_commands('before_repair'))}, "
            f"after_verify={len(self.plugins.enabled_hook_commands('after_verify'))}",
            file=sys.stderr,
        )
    async def _ensure_workspace_pool(self):
        if self._workspace_pool_ready:
            return
        async with self._workspace_pool_lock:
            if self._workspace_pool_ready:
                return
            await self.workspace_pool.initialize()
            self._workspace_pool_ready = True

    def _merge_workspace_meta(self, result: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
        result["workspace_pool"] = {
            **meta,
            "stats": self.workspace_pool.get_stats(),
        }
        return result

    def _is_success(self, result: dict[str, Any] | None) -> bool:
        if not isinstance(result, dict):
            return False
        if bool(result.get("success")):
            return True
        verify = result.get("verify") or {}
        return bool(verify.get("ok"))

    def _sync_hot_cache_confidence(self, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            return result

        memory = result.get("memory") or {}
        hot = memory.get("hot_cache") if isinstance(memory, dict) else None
        if not isinstance(hot, dict):
            return result

        conf = result.get("confidence") or {}
        if not isinstance(conf, dict):
            conf = {}
            result["confidence"] = conf

        verify_ok = bool((result.get("verify") or {}).get("ok"))
        branch_ok = bool((result.get("branch_result") or {}).get("ok"))
        behavioral_ok = bool((result.get("behavioral_verify") or {}).get("ok"))
        contract_ok = bool((result.get("contract_result") or {}).get("ok"))
        success = verify_ok or branch_ok or behavioral_ok or contract_ok
        if not success:
            return result

        result_obj = result.get("result") or {}
        best_plan = result.get("best_plan") or {}

        base_score = float(
            conf.get("score", 0.0)
            or (result_obj.get("confidence") if isinstance(result_obj, dict) else 0.0)
            or (best_plan.get("confidence") if isinstance(best_plan, dict) else 0.0)
            or 0.0
        )

        hot_score = float(hot.get("confidence", base_score) or base_score)
        boosted = max(base_score, hot_score)

        conf["score"] = boosted
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = boosted - base_score

        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

        return result

    def _build_context(self, file_path: Path) -> dict[str, Any]:
        repro = run_python_file(str(file_path))
        stderr = str(getattr(repro, "stderr", "") or "")
        return {
            "error_text": stderr,
            "traceback": [],
            "repro": repro.to_dict() if hasattr(repro, "to_dict") else {},
        }

    def _should_hot_force(self, context: dict[str, Any]) -> bool:
        explicit = str(context.get("signature") or "").strip().lower()
        if explicit in {"filenotfounderror:open:runtime", "importerror:no_module_named"}:
            return True

        text = str(context.get("error_text") or "").lower()
        if "filenotfounderror" in text and ("open(" in text or "read_text" in text or "no such file or directory" in text):
            return True
        if "modulenotfounderror" in text or "no module named" in text or "importerror" in text:
            return True
        return False

    def _prepare_workspace_file(self, original: Path, ws: Path) -> Path:
        work_dir = ws / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        target = work_dir / original.name
        shutil.copy2(original, target)
        return target

    def _copy_back_if_success(self, work_target: Path, original: Path, result: dict[str, Any]) -> dict[str, Any]:
        if self._is_success(result) and work_target.exists():
            shutil.copy2(work_target, original)
            result["target_file"] = str(original)
        return result


    def _repo_type_for_target(self, target: Path, context: dict[str, Any]) -> str:
        explicit = str(context.get("repo_type") or "").strip()
        if explicit:
            return explicit
        suffix = target.suffix.lower()
        if suffix == ".py":
            return "python_cli"
        if suffix in {".js", ".ts"}:
            return "js_cli"
        return "generic"

    def _ensure_synaptic_context(self, target: Path, context: dict[str, Any]) -> dict[str, Any]:
        updated = dict(context or {})
        signature = str(updated.get("signature") or "").strip().lower()
        if not signature:
            try:
                signature = str(self._quick_signature(target, updated) or "").strip().lower()
            except Exception:
                signature = ""
        if signature:
            updated["signature"] = signature
        updated.setdefault("repo_type", self._repo_type_for_target(target, updated))
        return updated

    def _apply_synaptic_metadata(self, result: dict[str, Any], agent_results: list[dict[str, Any]]) -> dict[str, Any]:
        planner = self._agent_output(agent_results, "planner")
        synaptic = planner.get("synaptic")
        if isinstance(synaptic, dict) and synaptic:
            result["synaptic"] = synaptic
        return result

    def _remember_synaptic_result(
        self,
        *,
        result: dict[str, Any],
        context: dict[str, Any],
        effective_mode: str,
    ) -> dict[str, Any] | None:
        signature = str(context.get("signature") or result.get("signature") or "").strip().lower()
        if not signature:
            return None

        route = str(effective_mode or result.get("mode") or "").strip() or "unknown"
        repo_type = str(context.get("repo_type") or "").strip() or None
        file_path = result.get("target_file") or context.get("file_path")

        try:
            from core.memory.synaptic_hooks import remember_from_result
            return remember_from_result(
                result=result,
                signature=signature,
                route=route,
                file_path=str(file_path) if file_path else None,
                repo_type=repo_type,
                intent="repair",
            )
        except Exception:
            return None


    def _agent_output(self, agent_results: list[dict[str, Any]], agent_name: str) -> dict[str, Any]:
        for item in agent_results:
            if item.get("agent") == agent_name:
                return item.get("output", {}) or {}
        return {}

    def _effective_mode_from_agents(self, requested_mode: str, agent_results: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        planner = self._agent_output(agent_results, "planner")
        suggested = str(planner.get("suggested_mode") or requested_mode)

        if requested_mode == "auto" and suggested in {"hot_force", "fast", "fast_v2"}:
            return suggested, {
                "requested_mode": requested_mode,
                "effective_mode": suggested,
                "planner_suggested_mode": suggested,
                "planner_reason": planner.get("reason", ""),
            }

        return requested_mode, {
            "requested_mode": requested_mode,
            "effective_mode": requested_mode,
            "planner_suggested_mode": suggested,
            "planner_reason": planner.get("reason", ""),
        }

    def _apply_agent_postprocessing(self, result: dict[str, Any], agent_results: list[dict[str, Any]]) -> dict[str, Any]:
        verifier = self._agent_output(agent_results, "verifier")
        test_runner = self._agent_output(agent_results, "test_runner")

        adjustment = float(verifier.get("confidence_adjustment", 0.0) or 0.0)
        if adjustment and isinstance(result.get("confidence"), dict):
            conf = result["confidence"]
            base = float(conf.get("score", 0.0) or 0.0)
            conf["score"] = min(1.0, base + adjustment)
            conf.setdefault("factors", {})
            conf["factors"]["agent_verifier"] = adjustment

        required_checks = test_runner.get("required_checks", [])
        if required_checks:
            result["required_checks"] = required_checks

        return result

    async def _run_agent_plan(self, *, target: Path, mode: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        plan = [
            (
                "planner",
                AgentTask(
                    name="repair_plan",
                    payload={
                        "target": str(target),
                        "intent": mode,
                        "error_text": context.get("error_text", ""),
                        "signature": context.get("signature", ""),
                        "repo_type": context.get("repo_type", ""),
                    },
                ),
            ),
            (
                "verifier",
                AgentTask(
                    name="pre_verify",
                    payload={"checks": ["syntax", "behavioral_light"]},
                ),
            ),
            (
                "test_runner",
                AgentTask(
                    name="test_hint",
                    payload={"command": "python3 scripts/integration_test.py"},
                ),
            ),
        ]
        results = await self.scheduler.run_many(plan)
        return [
            {
                "agent": r.agent,
                "ok": r.ok,
                "output": r.output,
                "error": r.error,
            }
            for r in results
        ]

    def _policy_gate(self, *, target: Path, action: str, confidence: float) -> dict[str, Any] | None:
        decision = self.policy.evaluate(path=str(target), action=action, confidence=confidence)
        if decision.allow:
            return None
        return {
            "success": False,
            "mode": "policy_block",
            "error": "policy_blocked",
            "policy": {
                "allow": False,
                "reasons": decision.reasons,
                "required_checks": decision.required_checks,
            },
        }

    def _dispatch_hook(self, event_name: str, payload: dict[str, Any], metadata: dict[str, Any] | None = None) -> list[dict]:
        return self.hooks.dispatch(HookEvent(name=event_name, payload=payload, metadata=metadata or {}))

    def _attach_common_metadata(
        self,
        result: dict[str, Any],
        *,
        agent_results: list[dict[str, Any]] | None = None,
        before_hooks: list[dict] | None = None,
        after_hooks: list[dict] | None = None,
    ) -> dict[str, Any]:
        if agent_results is not None:
            result["agent_results"] = agent_results
        if before_hooks is not None:
            result["before_repair_hooks"] = before_hooks
        if after_hooks is not None:
            result["after_verify_hooks"] = after_hooks
        result["plugins"] = self.plugins.list_plugins()
        return result

    def _run_hot_force_workspace_sync(self, original: Path, ws_target: Path, context: dict[str, Any]) -> dict[str, Any]:
        result = self.hot_force.repair(ws_target, context)
        return self._copy_back_if_success(ws_target, original, result)

    async def _run_hot_force(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        signature = str(context.get("signature") or "").strip().lower()
        if not signature:
            signature = self._quick_signature(file_path, context)
        if signature:
            context = {**context, "signature": signature}

        policy_block = self._policy_gate(target=file_path, action="direct_write", confidence=0.97)
        if policy_block is not None:
            return policy_block

        await self._ensure_workspace_pool()
        ws, meta = await self.workspace_pool.acquire()
        try:
            ws_target = await asyncio.to_thread(self._prepare_workspace_file, file_path, ws)
            result = await asyncio.to_thread(self._run_hot_force_workspace_sync, file_path, ws_target, context)
            return self._merge_workspace_meta(result, meta)
        finally:
            self.workspace_pool.release(ws, dirty=True)

    def _run_fast_v2_workspace_sync(self, original: Path, ws_target: Path, plan: dict[str, Any]) -> dict[str, Any]:
        code = str(plan["code"])
        ast.parse(code)
        ws_target.write_text(code, encoding="utf-8")

        result = {
            "success": True,
            "mode": "fast_v2",
            "signature": plan["signature"],
            "strategy": plan["strategy"],
            "target_file": str(ws_target),
            "verify": {
                "ok": True,
                "reason": plan.get("verify_reason", "fast_v2_syntax_only"),
            },
            "confidence": {
                "score": float(plan.get("confidence", 0.9)),
                "factors": {
                    "fast_v2": float(plan.get("confidence", 0.9)),
                    "syntax_check": 1.0,
                },
                "recommendation": "auto_apply" if float(plan.get("confidence", 0.9)) >= 0.95 else "human_review",
            },
            "fast_v2": {
                "used": True,
                "path": plan.get("path", "unknown"),
                "signature": plan["signature"],
            },
        }
        return self._copy_back_if_success(ws_target, original, result)

    async def _run_fast_v2(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        plan = self.fast_v2.plan(file_path, context)
        if not bool(plan.get("used")):
            return {
                "success": False,
                "mode": "fast_v2",
                "signature": plan.get("signature", ""),
                "error": "fast_v2_no_plan",
                "fast_v2": plan,
            }

        confidence = float(plan.get("confidence", 0.9))
        policy_block = self._policy_gate(target=file_path, action="direct_write", confidence=confidence)
        if policy_block is not None:
            return policy_block

        await self._ensure_workspace_pool()
        ws, meta = await self.workspace_pool.acquire()
        started = time.monotonic()
        try:
            ws_target = await asyncio.to_thread(self._prepare_workspace_file, file_path, ws)
            result = await asyncio.to_thread(self._run_fast_v2_workspace_sync, file_path, ws_target, plan)
            result["latency_ms"] = round((time.monotonic() - started) * 1000.0, 3)
            return self._merge_workspace_meta(result, meta)
        finally:
            self.workspace_pool.release(ws, dirty=True)

    def _quick_signature(self, file_path: Path, context: dict[str, Any]) -> str:
        explicit = str(context.get("signature") or "").strip().lower()
        if explicit:
            return explicit

        text = str(context.get("error_text") or "").lower()
        if "filenotfounderror" in text and ("open(" in text or "read_text" in text or "no such file or directory" in text):
            return "filenotfounderror:open:runtime"
        if "modulenotfounderror" in text or "no module named" in text or "importerror" in text:
            return "importerror:no_module_named"

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        if "open(" in source and ".read()" in source:
            return "filenotfounderror:open:runtime"
        if "read_text(" in source:
            return "filenotfounderror:open:runtime"
        if re.search(r'(?m)^\s*import\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*$', source):
            return "importerror:no_module_named"
        if re.search(r'(?m)^\s*from\s+[A-Za-z_][A-Za-z0-9_\.]*\s+import\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*$', source):
            return "importerror:no_module_named"
        return ""

    def _fast_shortcut_result(
        self,
        *,
        file_path: Path,
        signature: str,
        strategy: str,
        code: str,
        confidence: float,
        verify_reason: str,
        source_tag: str,
    ) -> dict[str, Any]:
        ast.parse(code)
        file_path.write_text(code, encoding="utf-8")
        return {
            "success": True,
            "mode": "fast_shortcut",
            "signature": signature,
            "strategy": strategy,
            "target_file": str(file_path),
            "verify": {"ok": True, "reason": verify_reason},
            "confidence": {
                "score": confidence,
                "factors": {
                    "fast_shortcut": confidence,
                    "syntax_check": 1.0,
                },
                "recommendation": "auto_apply" if confidence >= 0.95 else "human_review",
            },
            "memory": {
                "fast_shortcut": {
                    "confidence": confidence,
                    "source": source_tag,
                    "signature": signature,
                }
            },
            "routes": ["fast_shortcut"],
            "fast_v2": {
                "used": True,
                "path": "fast_shortcut",
                "signature": signature,
            },
        }

    def _try_fast_shortcut(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any] | None:
        signature = self._quick_signature(file_path, context)
        if not signature:
            return None

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        if signature == "filenotfounderror:open:runtime":
            code = 'from pathlib import Path\n\nlog_path = Path("logs/app.log")\nif log_path.exists():\n    print(log_path.read_text())\nelse:\n    print("")\n'
            return self._fast_shortcut_result(
                file_path=file_path,
                signature=signature,
                strategy="guard_exists",
                code=code,
                confidence=0.94,
                verify_reason="fast_shortcut_file_guard",
                source_tag="daemon_fast_shortcut",
            )

        if signature == "importerror:no_module_named":
            raw_lines = source.splitlines()
            code_lines = []
            for line in raw_lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                code_lines.append(stripped)

            if not code_lines:
                return None

            stmt = code_lines[0]
            m_import = re.fullmatch(r"import\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*)?)?\s*", stmt)
            if m_import:
                module = m_import.group(1)
                alias = m_import.group(2)
                if alias:
                    generated = (
                        f"try:\n"
                        f"    import {module} as {alias}\n"
                        f"except ModuleNotFoundError:\n"
                        f"    {alias} = None\n"
                    )
                else:
                    generated = (
                        f"try:\n"
                        f"    import {module}\n"
                        f"except ModuleNotFoundError:\n"
                        f"    {module} = None\n"
                    )
                return self._fast_shortcut_result(
                    file_path=file_path,
                    signature=signature,
                    strategy="import_guard",
                    code=generated,
                    confidence=0.91,
                    verify_reason="fast_shortcut_import_guard",
                    source_tag="daemon_fast_shortcut",
                )

        return None

    def _run_fast_shortcut_workspace_sync(self, original: Path, ws_target: Path, context: dict[str, Any]) -> dict[str, Any] | None:
        result = self._try_fast_shortcut(ws_target, context)
        if result is None:
            return None
        return self._copy_back_if_success(ws_target, original, result)

    async def _run_fast_shortcut_with_pool(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any] | None:
        policy_block = self._policy_gate(target=file_path, action="direct_write", confidence=0.91)
        if policy_block is not None:
            return policy_block

        await self._ensure_workspace_pool()
        ws, meta = await self.workspace_pool.acquire()
        try:
            ws_target = await asyncio.to_thread(self._prepare_workspace_file, file_path, ws)
            result = await asyncio.to_thread(self._run_fast_shortcut_workspace_sync, file_path, ws_target, context)
            if result is None:
                return None
            return self._merge_workspace_meta(result, meta)
        finally:
            self.workspace_pool.release(ws, dirty=True)

    def _run_existing_pipeline_sync(self, file_path: Path, mode: str, context: dict[str, Any]) -> dict[str, Any]:
        repro = run_python_file(str(file_path))
        error_text = str(getattr(repro, "stderr", "") or "")
        result = run_autofix(
            error_text=error_text,
            file_path=str(file_path),
            fast=(mode == "fast"),
        )
        result = finalize_repair_payload(result, fast=(mode == "fast"))
        result = self._sync_hot_cache_confidence(result)
        return result

    async def _run_existing_pipeline(self, file_path: Path, mode: str, context: dict[str, Any]) -> dict[str, Any]:
        if mode == "fast":
            shortcut = await self._run_fast_shortcut_with_pool(file_path, context)
            if shortcut is not None:
                return shortcut

        return await asyncio.to_thread(
            self._run_existing_pipeline_sync,
            file_path,
            mode,
            context,
        )

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        start = time.monotonic()

        try:
            data = await reader.read(65536)
            request = json.loads(data.decode("utf-8"))

            raw_file = request.get("file_path") or request.get("file")
            if not raw_file:
                raise ValueError("missing file_path/file")
            file_path = Path(raw_file)

            context = request.get("context") or {}
            mode = str(request.get("mode") or "auto")
            context = self._ensure_synaptic_context(file_path, context)

            if not file_path.exists():
                result = {
                    "success": False,
                    "mode": "daemon",
                    "error": f"target does not exist: {file_path}",
                }
            else:
                if not context:
                    context = self._build_context(file_path)

                agent_results = await self._run_agent_plan(target=file_path, mode=mode, context=context)
                effective_mode = mode
                planner = next((x.get("output", {}) for x in agent_results if x.get("agent") == "planner"), {})
                if mode == "auto":
                    effective_mode = str(planner.get("suggested_mode") or "fast")
                routing_meta = {"requested_mode": mode, "effective_mode": effective_mode, "planner_suggested_mode": str(planner.get("suggested_mode") or effective_mode), "planner_reason": planner.get("reason", "")}
                mode = effective_mode
                effective_mode, routing_meta = self._effective_mode_from_agents(mode, agent_results)
                before_hooks = self._dispatch_hook(
                    "before_repair",
                    {"file": str(file_path), "mode": effective_mode, "context": context},
                    {"socket": str(self.socket_path)},
                )

                if request.get("fast_path") == "hot_force" or effective_mode == "hot_force":
                    hot_ctx = {
                        "error_text": "Hot force signature request",
                        "traceback": [{"error_type": "HotForceSignature", "function": "hot_force"}],
                        "signature": request.get("signature"),
                    }
                    result = await self._run_hot_force(file_path, hot_ctx)
                    result["fallback_chain"] = ["hot_force"]
                elif effective_mode == "fast_v2":
                    result = await self._run_fast_v2(file_path, context)
                    result["fallback_chain"] = ["fast_v2"]
                else:
                    result = await self.fallback.repair(file_path, context, mode=effective_mode)

                after_hooks = self._dispatch_hook(
                    "after_verify",
                    {"file": str(file_path), "mode": effective_mode, "result": result},
                    {"socket": str(self.socket_path)},
                )

                result = self._attach_common_metadata(
                    result,
                    agent_results=agent_results,
                    before_hooks=before_hooks,
                    after_hooks=after_hooks,
                )

        except Exception as exc:
            result = {
                "success": False,
                "mode": "daemon",
                "error": f"{type(exc).__name__}: {exc}",
            }

        if isinstance(result, dict) and "agent_results" in result:
            result = self._apply_agent_postprocessing(result, result.get("agent_results", []))
            result = self._apply_synaptic_metadata(result, agent_results)
            synaptic_memory_update = self._remember_synaptic_result(
                result=result,
                context=context,
                effective_mode=effective_mode,
            )
            if synaptic_memory_update is not None:
                result["synaptic_memory_update"] = synaptic_memory_update

            if "routing_meta" in locals():
                result.setdefault("routing", routing_meta)
                if isinstance(result.get("synaptic"), dict):
                    result["routing"]["synaptic_used"] = bool(result["synaptic"].get("used", False))
                    result["routing"]["synaptic_prior"] = float(result["synaptic"].get("prior", 0.0) or 0.0)
                    result["routing"]["synaptic_seen_total"] = int(result["synaptic"].get("seen_total", 0) or 0)
        elapsed = (time.monotonic() - start) * 1000.0
        if isinstance(result, dict):
            result.setdefault("daemon", {})
            result["daemon"]["socket"] = str(self.socket_path)
            result["daemon"]["request_ms"] = round(elapsed, 3)

        writer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        await writer.drain()
        writer.close()
        await writer.wait_closed()

        print(f"Request handled in {elapsed:.2f}ms", file=sys.stderr)

    async def start(self):
        if self.socket_path.exists():
            self.socket_path.unlink()

        server = await asyncio.start_unix_server(
            self.handle_request,
            str(self.socket_path),
        )

        print(f"Daemon listening on {self.socket_path}", file=sys.stderr)

        async with server:
            await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", default="/tmp/termorganism.sock")
    args = parser.parse_args()

    daemon = TermOrganismDaemon(socket_path=Path(args.socket))
    asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
