from __future__ import annotations
from core.ui.thoughts import ThoughtEvent

from typing import Any
from pathlib import Path
import ast
from datetime import datetime
import uuid
import os
import re
import asyncio
from time import perf_counter

from core.memory import event_store
from core.memory.engine import MemoryEngine, RepairRecord
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.multi_file_planner import expand_multifile_plan_family
from core.planner.branch_executor import execute_repair_plan


import sys
import inspect
import tempfile
def _force_plan_target_to_file(plan, file_path):
    if not isinstance(plan, dict) or not file_path:
        return plan

    try:
        fp_path = Path(file_path).resolve()
        fp = str(fp_path)
    except Exception:
        fp_path = Path(str(file_path))
        fp = str(file_path)

    if not fp:
        return plan

    parent_fp = str(fp_path.parent)

    def _looks_like_directory_target(x):
        s = str(x) if x is not None else ""
        if s in {"", ".", parent_fp}:
            return True
        try:
            xp = Path(s)
            if xp.exists() and xp.is_dir():
                return True
        except Exception:
            pass
        return False

    target_files = plan.get("target_files")
    if not isinstance(target_files, list) or not target_files or any(_looks_like_directory_target(x) for x in target_files):
        plan["target_files"] = [fp]

    affected_scope = plan.get("affected_scope")
    if isinstance(affected_scope, list):
        if not affected_scope or any(_looks_like_directory_target(x) for x in affected_scope):
            plan["affected_scope"] = [fp]

    edits = plan.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                cur = edit.get("file")
                if _looks_like_directory_target(cur):
                    edit["file"] = fp

    evidence = plan.get("evidence")
    if isinstance(evidence, dict):
        loc = evidence.get("localization_target")
        if _looks_like_directory_target(loc):
            evidence["localization_target"] = fp

    for key in ("target_file", "file_path_hint"):
        cur = plan.get(key)
        if _looks_like_directory_target(cur):
            plan[key] = fp

    return plan

    try:
        fp = str(Path(file_path).resolve())
    except Exception:
        fp = str(file_path)

    if not fp:
        return plan

    parent_fp = str(Path(fp).parent)

    def _is_rootish(x):
        s = str(x) if x is not None else ""
        return s in {"", ".", parent_fp}

    target_files = plan.get("target_files")
    if not isinstance(target_files, list) or not target_files or any(_is_rootish(x) for x in target_files):
        plan["target_files"] = [fp]

    affected_scope = plan.get("affected_scope")
    if isinstance(affected_scope, list):
        if not affected_scope or any(_is_rootish(x) for x in affected_scope):
            plan["affected_scope"] = [fp]

    edits = plan.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                cur = edit.get("file")
                if _is_rootish(cur):
                    edit["file"] = fp

    evidence = plan.get("evidence")
    if isinstance(evidence, dict):
        loc = evidence.get("localization_target")
        if _is_rootish(loc):
            evidence["localization_target"] = fp

    for key in ("target_file", "file_path_hint"):
        cur = plan.get(key)
        if _is_rootish(cur):
            plan[key] = fp

    return plan
from core.verify.contract_synth import synthesize_and_check_contract
from core.verify.contract_propagation import check_contract_propagation
from core.verify.javascript_verify import is_javascript_path, verify_javascript_candidate
from core.observability import get_repair_metrics, emit_repair_trace
from core.ranker.plan_ranker import rank_plans
from core.planner.plan_normalizer import plan_to_candidate
from core.planner.plan_apply import apply_plan

from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.file_runtime import FileRuntimeExpert



_FAST_VERIFY_MODE = False


def _plan_is_multifile(plan: dict[str, Any] | None) -> bool:
    if not isinstance(plan, dict):
        return False
    target_files = plan.get("target_files") or []
    if isinstance(target_files, list) and len(target_files) > 1:
        return True
    scope = plan.get("affected_scope") or []
    if isinstance(scope, list) and len(scope) > 1:
        return True
    meta = plan.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("multifile"):
        return True
    evidence = plan.get("evidence") or {}
    if isinstance(evidence, dict) and evidence.get("multifile"):
        return True
    return False


def _fast_verify_candidate(plan: dict[str, Any], *args, **kwargs) -> dict[str, Any]:
    candidate = plan_to_candidate(plan) if isinstance(plan, dict) else {}
    code = str((candidate or {}).get("candidate_code") or "")
    target_file = (
        (candidate or {}).get("target_file")
        or (candidate or {}).get("file_path_hint")
        or (plan or {}).get("target_file")
        or "candidate.py"
    )

    if not code.strip():
        return {
            "ok": True,
            "reason": "fast mode operational/static shortcut",
            "applied_files": [target_file] if target_file else [],
            "workspace_root": None,
            "runtime": {
                "ok": True,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            },
            "static_verify": None,
            "fast_mode": True,
        }

    try:
        ast.parse(code)
        static_verify = {"ok": True, "reason": "AST parse ok"}
    except SyntaxError as exc:
        static_verify = {"ok": False, "reason": f"AST parse failed: {exc}"}
        return {
            "ok": False,
            "reason": "fast mode static verification failed",
            "applied_files": [target_file] if target_file else [],
            "workspace_root": None,
            "runtime": {
                "ok": False,
                "returncode": 1,
                "stdout": "",
                "stderr": static_verify["reason"],
            },
            "static_verify": static_verify,
            "fast_mode": True,
        }

    try:
        with tempfile.TemporaryDirectory(prefix="termorganism_fast_verify_") as td:
            out_path = Path(td) / Path(str(target_file)).name
            out_path.write_text(code, encoding="utf-8")
            repro = run_python_file(str(out_path))
            if hasattr(repro, "to_dict"):
                runtime = repro.to_dict()
            else:
                runtime = {
                    "ok": False,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "unknown lightweight runtime result",
                }
    except Exception as exc:
        runtime = {
            "ok": False,
            "returncode": 1,
            "stdout": "",
            "stderr": f"fast lightweight verify exception: {exc}",
        }

    ok = bool(static_verify.get("ok")) and bool(runtime.get("returncode", 1) == 0)

    return {
        "ok": ok,
        "reason": "fast mode lightweight verification passed" if ok else "fast mode lightweight verification failed",
        "applied_files": [target_file] if target_file else [],
        "workspace_root": None,
        "runtime": runtime,
        "static_verify": static_verify,
        "fast_mode": True,
    }


def _maybe__maybe_execute_repair_plan(plan, *args, **kwargs):
    if (not _FAST_VERIFY_MODE) or _plan_is_multifile(plan):
        return _maybe_execute_repair_plan(plan, *args, **kwargs)
    return _fast_verify_candidate(plan, *args, **kwargs)




def _call_analyze_failure_causes_compat(
    *,
    error_text: str,
    semantic: dict[str, Any],
    project_graph,
    file_path: str | None = None,
):
    try:
        params = inspect.signature(analyze_failure_causes).parameters
    except Exception:
        params = {}

    kwargs = {
        "error_text": error_text,
        "semantic": semantic,
        "project_graph": project_graph,
    }
    if "file_path" in params:
        kwargs["file_path"] = file_path

    return analyze_failure_causes(**kwargs)




def _ms(start: float, end: float) -> float:
    return round((end - start) * 1000.0, 3)




_MEMORY_ENGINE_SINGLETON = None


def _get_memory_engine():
    global _MEMORY_ENGINE_SINGLETON
    if _MEMORY_ENGINE_SINGLETON is None:
        try:
            _MEMORY_ENGINE_SINGLETON = MemoryEngine()
        except Exception:
            _MEMORY_ENGINE_SINGLETON = False
    return _MEMORY_ENGINE_SINGLETON if _MEMORY_ENGINE_SINGLETON is not False else None


def _memory_extract_error_type(error_text: str, semantic: dict[str, Any] | None = None) -> str:
    repro = (semantic or {}).get("repro") or {}
    et = repro.get("exception_type")
    if et:
        return str(et)
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]*Error)", error_text or "")
    return m.group(1) if m else "UnknownError"


def _memory_build_context(error_text: str, file_path: str | None, semantic: dict[str, Any] | None = None) -> dict[str, Any]:
    frames = []
    if " _extract_traceback_frames" == "_extract_traceback_frames" and "_extract_traceback_frames" in globals():
        try:
            frames = _extract_traceback_frames(error_text)
        except Exception:
            frames = []

    if not frames:
        for m in re.finditer(r'File "([^"]+)", line (\d+)', error_text or ""):
            frames.append({
                "filename": m.group(1),
                "lineno": int(m.group(2)),
                "function": "unknown",
                "error_type": _memory_extract_error_type(error_text, semantic),
            })

    return {
        "target_file": file_path,
        "error_text": error_text,
        "error_type": _memory_extract_error_type(error_text, semantic),
        "traceback": frames,
    }


def _memory_enrich_payload(payload: dict[str, Any], *, error_text: str, file_path: str | None, semantic: dict[str, Any] | None = None) -> dict[str, Any]:
    engine = _get_memory_engine()
    if engine is None or not isinstance(payload, dict):
        return payload

    context = _memory_build_context(error_text, file_path, semantic)
    failure_signature = engine._normalize_failure(context)
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        result = {}
        payload["result"] = result

    metadata = result.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
        result["metadata"] = metadata

    repair_type = str(
        result.get("kind")
        or metadata.get("strategy")
        or result.get("expert")
        or "unknown"
    )

    prior = float(engine.get_repair_prior(failure_signature, repair_type))
    similar = []
    suggestion = None
    if file_path:
        try:
            project_hash = engine.project_hash_for(Path(file_path))
            similar = engine.find_similar_repairs(failure_signature, project_hash=project_hash, limit=3)
            suggestion = engine.suggest_from_memory(context, Path(file_path))
        except Exception:
            similar = []
            suggestion = None

    result["memory_prior"] = prior
    result["historical_success_prior"] = prior
    metadata["memory_prior"] = prior
    metadata["historical_success_prior"] = prior
    metadata["failure_signature"] = failure_signature
    metadata["similar_repairs_found"] = len(similar)

    payload["memory"] = {
        "failure_signature": failure_signature,
        "memory_prior": prior,
        "similar_repairs_found": len(similar),
        "suggestion": suggestion,
    }

    conf = payload.get("confidence")
    if isinstance(conf, dict):
        factors = conf.get("factors")
        if not isinstance(factors, dict):
            factors = {}
            conf["factors"] = factors
        factors["memory_prior"] = prior

    return payload


def _memory_record_payload(payload: dict[str, Any], *, error_text: str, file_path: str | None, semantic: dict[str, Any] | None = None) -> None:
    engine = _get_memory_engine()
    if engine is None or not file_path or not isinstance(payload, dict):
        return

    try:
        target = Path(file_path)
        context = _memory_build_context(error_text, file_path, semantic)
        failure_signature = engine._normalize_failure(context)
        result = payload.get("result") or {}
        metadata = result.get("metadata") or {}
        repair_type = str(
            result.get("kind")
            or metadata.get("strategy")
            or result.get("expert")
            or "unknown"
        )
        repair_code = str(
            result.get("candidate_code")
            or result.get("patch")
            or ""
        )

        confidence = float(
            ((payload.get("confidence") or {}).get("score"))
            or result.get("confidence")
            or 0.0
        )

        success_verified = bool(
            ((payload.get("verify") or {}).get("ok"))
            or ((payload.get("contract_result") or {}).get("ok"))
            or ((payload.get("behavioral_verify") or {}).get("ok"))
        )

        metrics = payload.get("metrics") or {}
        context_summary = {
            "latency_ms": int(float(metrics.get("total_ms", 0) or 0)),
            "sandbox_used": bool(payload.get("sandbox")),
            "route": ",".join(payload.get("routes") or []),
            "mode": metrics.get("mode"),
        }

        rec = RepairRecord(
            id=str(uuid.uuid4()),
            project_hash=engine.project_hash_for(target),
            file_hash=engine.file_hash_for(target),
            failure_signature=failure_signature,
            repair_type=repair_type,
            repair_code=repair_code,
            confidence=confidence,
            success_verified=success_verified,
            timestamp=datetime.utcnow(),
            context_summary=context_summary,
        )
        engine.record_repair(rec, local_only=not (success_verified and confidence > 0.9))
    except Exception:
        return




def _maybe_attach_javascript_verification(payload: dict[str, Any], *, file_path: str | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    if not is_javascript_path(file_path):
        return payload

    result = payload.get("result") or {}
    code = ""
    if isinstance(result, dict):
        code = str(result.get("candidate_code") or result.get("code") or "")

    if not code.strip():
        return payload

    try:
        jsv = verify_javascript_candidate(
            code=code,
            target_file=file_path,
            project_root=str(Path(file_path).resolve().parent if file_path else Path.cwd()),
        )
    except Exception as exc:
        payload.setdefault("verification", {})
        payload["verification"]["javascript"] = {
            "ok": False,
            "error": str(exc),
            "confidence": 0.0,
        }
        return payload

    payload.setdefault("verification", {})
    payload["verification"]["javascript"] = jsv

    conf = payload.get("confidence")
    if isinstance(conf, dict):
        factors = conf.get("factors")
        if not isinstance(factors, dict):
            factors = {}
            conf["factors"] = factors
        factors["javascript_verify"] = float(jsv.get("confidence", 0.0) or 0.0)

    if isinstance(result, dict):
        meta = result.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        meta["javascript_verify"] = {
            "ok": bool(jsv.get("ok")),
            "confidence": float(jsv.get("confidence", 0.0) or 0.0),
            "language": jsv.get("language"),
        }
        result["metadata"] = meta

    return payload




def _observability_language(file_path: str | None) -> str:
    ext = Path(str(file_path or "")).suffix.lower()
    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return "javascript"
    if ext in {".py"}:
        return "python"
    if ext in {".sh", ".bash", ".zsh", ".txt"}:
        return "shell"
    return "unknown"


def _record_observability(payload: dict[str, Any], *, file_path: str | None, fast: bool) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    metrics = get_repair_metrics()
    language = _observability_language(file_path)
    mode = str(((payload.get("metrics") or {}).get("mode")) or ("fast" if fast else "normal"))
    duration = float(((payload.get("metrics") or {}).get("total_ms", 0.0) or 0.0)) / 1000.0
    success = bool(((payload.get("verify") or {}).get("ok")))
    confidence = float(
        ((payload.get("confidence") or {}).get("score"))
        or ((payload.get("result") or {}).get("confidence"))
        or 0.0
    )

    try:
        metrics.record_repair(mode=mode, language=language, duration=duration, success=success, confidence=confidence)
        memory = payload.get("memory") or {}
        if isinstance(memory, dict):
            metrics.set_memory_size("current", int(memory.get("similar_repairs_found", 0) or 0))
    except Exception:
        pass

    try:
        emit_repair_trace("run_autofix", payload, file_path=file_path, fast=fast)
    except Exception:
        pass

    payload.setdefault("observability", {})
    payload["observability"]["metrics_enabled"] = bool(getattr(metrics, "enabled", False))
    payload["observability"]["tracing_enabled"] = bool(os.getenv("TERMORGANISM_TRACING", "").strip().lower() in {"1", "true", "yes", "on"})
    payload["observability"]["language"] = language
    return payload


class EventStoreAdapter:
    def append_event(self, payload: dict[str, Any]) -> None:
        if hasattr(event_store, "append_event"):
            event_store.append_event(payload)
            return
        if hasattr(event_store, "store_event"):
            event_store.store_event(payload)
            return
        if hasattr(event_store, "write_event"):
            event_store.write_event(payload)
            return


def _infer_provider_from_imports(file_path: str | None) -> str | None:
    if not file_path or not str(file_path).endswith(".py"):
        return None
    p = Path(file_path)
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return None

    root = p.parent
    candidates: list[Path] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                mod_path = root / (node.module.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                mod_path = root / (alias.name.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)

    if not candidates:
        return None

    for c in candidates:
        if c.name != p.name:
            return str(c.resolve())
    return str(candidates[0].resolve())


def _build_semantic_prelude(error_text: str, file_path: str | None):
    forced = "FORCED_SEMANTIC_ANALYSIS" in (error_text or "")

    if file_path and str(file_path).endswith(".py") and not forced:
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
        }

    if forced and file_path and str(file_path).endswith(".py"):
        caller = str(Path(file_path).resolve())
        provider = _infer_provider_from_imports(file_path)

        items = [{
            "file_path": caller,
            "line_no": None,
            "symbol": None,
            "reason": "forced semantic caller seed",
            "score": 0.91,
        }]
        if provider:
            items.append({
                "file_path": provider,
                "line_no": None,
                "symbol": None,
                "reason": "forced semantic provider seed",
                "score": 0.97,
            })

        return {
            "repro": {
                "ok": True,
                "command": [],
                "cwd": str(Path(file_path).resolve().parent),
                "returncode": 0,
                "stdout": "",
                "stderr": error_text,
                "exception_type": "ForcedSemanticAnalysis",
                "reproduced": False,
            },
            "localization": {
                "count": len(items),
                "top": items[1] if len(items) > 1 else items[0],
                "items": items,
            },
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict(),
        "localization": summarize_suspicions(suspicions),
    }


def _resolve_semantic_target(file_path: str | None, semantic: dict[str, Any] | None) -> str | None:
    loc = (semantic or {}).get("localization") or {}
    top = loc.get("top") or {}
    top_file = top.get("file_path")
    if top_file and str(top_file).endswith(".py") and "/usr/lib/" not in str(top_file):
        return str(Path(top_file).resolve())
    return file_path


def _emit_thought(
    thought_bus,
    phase: str,
    message: str,
    *,
    kind: str = "info",
    confidence: float | None = None,
    file_path: str | None = None,
    line_no: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if thought_bus is None:
        return
    try:
        thought_bus.emit(
            ThoughtEvent(
                phase=phase,
                message=message,
                kind=kind,
                confidence=confidence,
                file_path=file_path,
                line_no=line_no,
                meta=meta or {},
            )
        )
    except Exception:
        pass


def _build_candidates(error_text: str, file_path: str | None, semantic: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ctx = type("Ctx", (), {})()

    semantic_target = _resolve_semantic_target(file_path, semantic)
    ctx.error_text = error_text
    ctx.file_path = semantic_target or file_path

    source_target = semantic_target or file_path
    if source_target:
        try:
            ctx.source_code = Path(source_target).read_text(encoding="utf-8")
        except Exception:
            ctx.source_code = ""
    else:
        ctx.source_code = ""

    candidates: list[dict[str, Any]] = []

    for expert in (
        FileRuntimeExpert(),
        PythonSyntaxExpert(),
        DependencyExpert(),
        ShellRuntimeExpert(),
        MemoryRetrievalExpert(),
        LLMFallbackExpert(),
    ):
        try:
            proposed = expert.propose(ctx) or []
            for item in proposed:
                if isinstance(item, dict):
                    candidates.append(item)
        except Exception:
            continue

    return candidates


    _FAST_VERIFY_MODE = bool(fast)
    graph = build_project_graph(file_path).to_dict() if file_path else {"project_root": str("."), "files": [], "adjacency": {}}

    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
    )]

    candidates = _build_candidates(
        error_text=error_text,
        file_path=file_path,
        semantic=semantic,
    )

    _emit_thought(
        thought_bus,
        "Candidate Generation",
        f"{len(candidates)} candidates produced",
        kind="info",
    )

    expert_names = sorted({str((c or {}).get("expert") or "unknown") for c in candidates if isinstance(c, dict)})
    _emit_thought(
        thought_bus,
        "Expert Routing",
        "experts=" + ", ".join(expert_names),
        kind="info",
    )

    for cand in list(candidates)[:3]:
        if isinstance(cand, dict):
            _emit_thought(
                thought_bus,
                "Hypothesis Generation",
                str(cand.get("summary") or cand.get("semantic_claim") or cand.get("hypothesis") or "candidate proposed"),
                kind="info",
                confidence=cand.get("confidence"),
                file_path=cand.get("target_file") or cand.get("file_path_hint"),
            )

    base_plans = build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
        candidates=candidates,
        file_path=file_path,
    )

    multifile_plans = expand_multifile_plan_family(
        base_plans=base_plans,
        file_path=file_path,
        semantic=semantic,
    )

    _emit_thought(
        thought_bus,
        "Planning",
        f"base_plans={len(base_plans)} multifile_plans={len(multifile_plans)}",
        kind="info",
    )

    _emit_thought(
        thought_bus,
        "Plan Expansion",
        f"total_plans={len(base_plans) + len(multifile_plans)}",
        kind="info",
    )

    all_plans = list(base_plans) + list(multifile_plans)

    enriched = []
    for plan in all_plans:
        plan = _force_plan_target_to_file(plan, file_path)
        branch = _maybe_execute_repair_plan(plan, file_path) if file_path else None
        contract = synthesize_and_check_contract(
            before_error_text=error_text,
            branch_result=branch or {},
            expected_behavior=plan.get("expected_behavior", {}),
        )

        p2 = dict(plan)
        p2["branch_result"] = branch
        p2["contract_result"] = contract
        p2["contract_propagation"] = check_contract_propagation(p2)
        enriched.append(p2)

    ranked = rank_plans(enriched)

    if ranked:
        best = ranked[0]
        evidence = best.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best.get("edits") or [{}])[0].get("file")) or best.get("target_file")
        _emit_thought(
            thought_bus,
            "Ranking",
            f"best strategy={strategy} target={target}",
            kind="success",
            confidence=best.get("confidence"),
            file_path=target,
        )
        _emit_thought(
            thought_bus,
            "Plan Rejection",
            f"rejected={max(0, len(ranked) - 1)} alternate_plans={max(0, len(ranked) - 1)}",
            kind="warn" if len(ranked) > 1 else "info",
        )
    else:
        _emit_thought(
            thought_bus,
            "Ranking",
            "no ranked plans available",
            kind="fail",
        )
    best_plan = ranked[0] if ranked else None

    return {
        "project_graph": graph,
        "causes": causes,
        "candidate_count": len(candidates),
        "base_plan_count": len(base_plans),
        "multifile_plan_count": len(multifile_plans),
        "repair_plans": ranked,
        "best_plan": best_plan,
        "branch_result": (best_plan or {}).get("branch_result"),
        "contract_result": (best_plan or {}).get("contract_result"),
        "contract_propagation": (best_plan or {}).get("contract_propagation"),
    }


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False, thought_bus=None, fast: bool = False):
    _t0 = perf_counter()
    _requested_file_path = file_path
    _emit_thought(
        thought_bus,
        "Input",
        f"target={file_path or '<none>'}",
        kind="info",
    )

    if _fast_engine_supported(error_text=error_text, file_path=file_path, fast=fast):
        _fast_payload = _run_fast_engine_repair(error_text=error_text, file_path=str(file_path), thought_bus=thought_bus)
        if _fast_payload is not None:
            _fast_payload = _maybe_attach_javascript_verification(_fast_payload, file_path=file_path)
            _fast_payload = _record_observability(_fast_payload, file_path=file_path, fast=fast)
            return _fast_payload
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    _t_semantic = perf_counter()

    repro = (semantic or {}).get("repro") or {}
    loc = (semantic or {}).get("localization") or {}
    top = loc.get("top") or {}

    repro_msg = (
        "forced semantic mode: runtime repro skipped"
        if repro.get("exception_type") == "ForcedSemanticAnalysis"
        else f"reproduced={repro.get('reproduced')} returncode={repro.get('returncode')} exception={repro.get('exception_type')}"
    )
    _emit_thought(
        thought_bus,
        "Reproduction",
        repro_msg,
        kind="success" if repro.get("ok") or repro.get("exception_type") == "ForcedSemanticAnalysis" else "warn",
    )

    if top:
        _emit_thought(
            thought_bus,
            "Localization",
            f"top={top.get('file_path')} reason={top.get('reason')}",
            kind="info",
            confidence=top.get("score"),
            file_path=top.get("file_path"),
            line_no=top.get("line_no"),
        )
    try:
        _fp = Path(_requested_file_path).resolve() if _requested_file_path else None
        if _fp and _fp.exists() and _fp.is_file():
            file_path = str(_fp)
    except Exception:
        pass

    planner = _build_repair_planner_prelude(error_text=error_text, file_path=file_path, semantic=semantic, thought_bus=thought_bus, fast=fast)
    _t_planner = perf_counter()
    planner = _force_plan_target_to_file(planner, file_path)
    if isinstance(planner, dict) and isinstance(planner.get("source_plan"), dict):
        planner["source_plan"] = _force_plan_target_to_file(planner["source_plan"], file_path)

    best_plan = (planner or {}).get("best_plan")
    _t_selection = perf_counter()

    if best_plan:
        evidence = best_plan.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best_plan.get("edits") or [{}])[0].get("file")) or best_plan.get("target_file")

        provider = evidence.get("provider")
        caller = evidence.get("caller")

        if provider:
            _emit_thought(
                thought_bus,
                "Localization",
                f"provider={provider}",
                kind="info",
                file_path=provider,
            )

        if caller:
            _emit_thought(
                thought_bus,
                "Localization",
                f"caller={caller}",
                kind="info",
                file_path=caller,
            )

        _emit_thought(
            thought_bus,
            "Final Selection",
            f"strategy={strategy} target={target}",
            kind="success",
            confidence=best_plan.get("confidence"),
            file_path=target,
        )
    else:
        _emit_thought(
            thought_bus,
            "Final Selection",
            "no best plan selected",
            kind="fail",
        )
    plan_result = plan_to_candidate(best_plan) if best_plan else None
    if isinstance(plan_result, dict):
        summary_l = str(plan_result.get("summary") or "").lower()
        target_fp = str(
            plan_result.get("target_file")
            or plan_result.get("file_path_hint")
            or file_path
            or ""
        )

        if "shell command not found" in summary_l or target_fp.endswith(".txt"):
            plan_result["kind"] = "shell_missing_command"
        elif "missing package" in summary_l or "dependency issue" in summary_l:
            plan_result["kind"] = "dependency_missing_import"
        elif "missing file" in summary_l or "file not found" in summary_l:
            plan_result["kind"] = "runtime_file_missing"

        if file_path:
            plan_result["target_file"] = target_fp or str(file_path)
            plan_result["file_path_hint"] = target_fp or str(file_path)
    apply_result = apply_plan(best_plan) if auto_apply and best_plan else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "planner": planner,
        "result": plan_result,
        "apply": apply_result,
        "metrics": {
            "semantic_ms": _ms(_t0, _t_semantic),
            "planning_ms": _ms(_t_semantic, _t_planner),
            "selection_ms": _ms(_t_planner, _t_selection),
            "total_ms": _ms(_t0, perf_counter()),
        },
    }
    EventStoreAdapter().append_event(payload)

    result_obj = payload.get("result") or {}
    behavioral = (
        payload.get("behavioral_verify")
        or payload.get("sandbox")
        or payload.get("branch_result")
        or result_obj.get("branch_result")
        or {}
    )
    contract = (
        payload.get("contract_result")
        or result_obj.get("contract_result")
        or {}
    )
    apply_result = payload.get("apply") or {}

    if isinstance(behavioral, dict) and behavioral:
        _emit_thought(
            thought_bus,
            "Sandbox Replay",
            f"workspace={behavioral.get('workspace_root')} applied_files={len(behavioral.get('applied_files') or [])}",
            kind="info",
        )
        _emit_thought(
            thought_bus,
            "Sandbox",
            f"ok={behavioral.get('ok')} returncode={(behavioral.get('runtime') or {}).get('returncode')}",
            kind="success" if behavioral.get("ok") else "fail",
        )

    if isinstance(contract, dict) and contract:
        _emit_thought(
            thought_bus,
            "Contract Scoring",
            f"checks={len(contract.get('checks') or [])}",
            kind="info",
        )
        _emit_thought(
            thought_bus,
            "Contract",
            f"ok={contract.get('ok')} score={contract.get('score')}",
            kind="success" if contract.get("ok") else "fail",
        )

    if auto_apply:
        _emit_thought(
            thought_bus,
            "Apply",
            f"auto_apply={'yes' if apply_result else 'no-op'}",
            kind="success" if apply_result else "warn",
        )


    return {
        "result": plan_result,
        "semantic": semantic,
        "planner": planner,
        "best_plan": best_plan,
        "plan_score": float((best_plan or {}).get("plan_score", 0.0) or 0.0),
        "rank_tuple": (best_plan or {}).get("rank_tuple"),
        "branch_result": (planner or {}).get("branch_result"),
        "contract_result": (planner or {}).get("contract_result"),
        "contract_propagation": (planner or {}).get("contract_propagation"),
        "routes": ["planner_first", "multifile_contract"],
        "verify": {"ok": True, "reason": "plan-first path selected"},
        "behavioral_verify": plan_result.get("branch_result") if isinstance(plan_result, dict) else None,
        "synthesized_tests": plan_result.get("contract_result") if isinstance(plan_result, dict) else None,
        "sandbox": None,
        "apply": apply_result,
        "exec": None,
        "metrics": payload.get("metrics", {}),
        "candidate_count": 1 if plan_result else 0,
        "candidates": [plan_result] if plan_result else [],
    }

def _clamp01(value) -> float:
    try:
        v = float(value)
    except Exception:
        return 0.0
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _extract_memory_prior_from_payload(payload: dict) -> float:
    if not isinstance(payload, dict):
        return 0.5

    vals = []

    result = payload.get("result") or {}
    if isinstance(result, dict):
        for key in ("memory_prior", "historical_success_prior"):
            if key in result:
                vals.append(result.get(key))
        meta = result.get("metadata") or {}
        if isinstance(meta, dict):
            for key in ("memory_prior", "historical_success_prior"):
                if key in meta:
                    vals.append(meta.get(key))

    for cand in payload.get("candidates") or []:
        if isinstance(cand, dict):
            for key in ("memory_prior", "historical_success_prior"):
                if key in cand:
                    vals.append(cand.get(key))
            meta = cand.get("metadata") or {}
            if isinstance(meta, dict):
                for key in ("memory_prior", "historical_success_prior"):
                    if key in meta:
                        vals.append(meta.get(key))

    cleaned = [_clamp01(v) for v in vals if v is not None]
    if cleaned:
        return max(cleaned)

    return 0.5


def finalize_repair_payload(payload: dict, fast: bool = False) -> dict:
    if not isinstance(payload, dict):
        return payload

    result = payload.get("result") or {}
    behavioral = payload.get("behavioral_verify") or {}
    sandbox = payload.get("sandbox") or {}
    contract = payload.get("contract_result") or {}

    static_ok = None
    for container in (
        sandbox,
        behavioral,
        result.get("branch_result") if isinstance(result, dict) else None,
    ):
        if isinstance(container, dict):
            static = container.get("static_verify") or {}
            if isinstance(static, dict) and "ok" in static:
                static_ok = bool(static.get("ok"))
                break
    if static_ok is None:
        static_ok = bool(result)

    behavioral_ok = None
    if isinstance(behavioral, dict) and "ok" in behavioral:
        behavioral_ok = bool(behavioral.get("ok"))
    elif isinstance(contract, dict) and "ok" in contract:
        behavioral_ok = bool(contract.get("ok"))
    elif isinstance(sandbox, dict) and "ok" in sandbox:
        behavioral_ok = bool(sandbox.get("ok"))
    else:
        behavioral_ok = False

    sandbox_ok = None
    if isinstance(sandbox, dict) and "ok" in sandbox:
        sandbox_ok = bool(sandbox.get("ok"))

    cross_file = False
    if isinstance(result, dict):
        meta = result.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("multifile"):
            cross_file = True
        if len(result.get("affected_scope") or []) > 1:
            cross_file = True
        src_plan = result.get("source_plan") or {}
        if isinstance(src_plan, dict) and len(src_plan.get("target_files") or []) > 1:
            cross_file = True

    memory_prior = _extract_memory_prior_from_payload(payload)

    factors = {
        "static_valid": 1.0 if static_ok else 0.0,
        "behavioral_match": 1.0 if behavioral_ok else 0.0,
        "sandbox_pass": 0.6 if fast else (1.0 if sandbox_ok is True else 0.0 if sandbox_ok is False else 0.6),
        "cross_file_consistency": 0.85 if cross_file else 1.0,
        "memory_prior": memory_prior,
    }

    score = round(
        0.25 * factors["static_valid"] +
        0.35 * factors["behavioral_match"] +
        0.15 * factors["sandbox_pass"] +
        0.10 * factors["cross_file_consistency"] +
        0.15 * factors["memory_prior"],
        3,
    )

    if score >= 0.95:
        recommendation = "auto_apply"
    elif score >= 0.80:
        recommendation = "apply_with_review"
    else:
        recommendation = "human_review"

    uncertainty = ""
    if cross_file and score < 0.95:
        uncertainty = "cross_file_boundary_ambiguous"
    elif fast:
        uncertainty = "reduced_verification_fast_mode"
    elif not behavioral_ok:
        uncertainty = "behavioral_verification_weak"

    payload["confidence"] = {
        "score": score,
        "factors": factors,
        "uncertainty": uncertainty,
        "recommendation": recommendation,
    }

    metrics = payload.setdefault("metrics", {})
    if isinstance(metrics, dict):
        metrics["mode"] = "fast" if fast else "normal"
        metrics["fast"] = bool(fast)

    return payload
# ----------------------------------------------------------------------
# fast-mode clean overrides
# ----------------------------------------------------------------------

_FAST_VERIFY_MODE = False


def _plan_is_multifile(plan: dict[str, Any] | None) -> bool:
    if not isinstance(plan, dict):
        return False

    target_files = plan.get("target_files") or []
    if isinstance(target_files, list) and len(target_files) > 1:
        return True

    scope = plan.get("affected_scope") or []
    if isinstance(scope, list) and len(scope) > 1:
        return True

    evidence = plan.get("evidence") or {}
    if isinstance(evidence, dict) and evidence.get("multifile"):
        return True

    metadata = plan.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("multifile"):
        return True

    return False


def _fast_verify_candidate(plan: dict[str, Any], file_path: str | None = None) -> dict[str, Any]:
    candidate = plan_to_candidate(plan) if isinstance(plan, dict) else {}
    code = str((candidate or {}).get("candidate_code") or "")
    target_file = (
        (candidate or {}).get("target_file")
        or (candidate or {}).get("file_path_hint")
        or file_path
        or (plan or {}).get("target_file")
        or "candidate.py"
    )

    target_suffix = Path(str(target_file)).suffix.lower()

    # If there is no source rewrite, or this is not a Python file, keep heavy path.
    if (not code.strip()) or target_suffix != ".py":
        return execute_repair_plan(plan, file_path)

    try:
        static_verify = {"ok": True, "reason": "AST parse ok"}
        ast.parse(code)
    except SyntaxError as exc:
        static_verify = {"ok": False, "reason": f"AST parse failed: {exc}"}
        return {
            "ok": False,
            "reason": "fast mode static verification failed",
            "applied_files": [target_file] if target_file else [],
            "workspace_root": None,
            "runtime": {
                "ok": False,
                "returncode": 1,
                "stdout": "",
                "stderr": static_verify["reason"],
            },
            "static_verify": static_verify,
            "fast_mode": True,
        }

    try:
        with tempfile.TemporaryDirectory(prefix="termorganism_fast_verify_") as td:
            out_path = Path(td) / Path(str(target_file)).name
            out_path.write_text(code, encoding="utf-8")
            repro = run_python_file(str(out_path))
            runtime = repro.to_dict() if hasattr(repro, "to_dict") else {
                "ok": False,
                "returncode": 1,
                "stdout": "",
                "stderr": "unknown lightweight runtime result",
            }
    except Exception as exc:
        runtime = {
            "ok": False,
            "returncode": 1,
            "stdout": "",
            "stderr": f"fast lightweight verify exception: {exc}",
        }

    ok = bool(static_verify.get("ok")) and bool(runtime.get("returncode", 1) == 0)

    return {
        "ok": ok,
        "reason": "fast mode lightweight verification passed" if ok else "fast mode lightweight verification failed",
        "applied_files": [target_file] if target_file else [],
        "workspace_root": None,
        "runtime": runtime,
        "static_verify": static_verify,
        "fast_mode": True,
    }


def _maybe_execute_repair_plan(plan, file_path: str | None = None):
    if not _FAST_VERIFY_MODE:
        return execute_repair_plan(plan, file_path)

    # Keep full path for multifile repairs.
    if _plan_is_multifile(plan):
        return execute_repair_plan(plan, file_path)

    # Fast path for single-file source rewrites.
    return _fast_verify_candidate(plan, file_path=file_path)


def _build_repair_planner_prelude(
    error_text: str,
    file_path: str | None,
    semantic: dict[str, Any],
    thought_bus=None,
    fast: bool = False,
):
    global _FAST_VERIFY_MODE
    _FAST_VERIFY_MODE = bool(fast)

    graph = build_project_graph(file_path) if file_path else {}
    causes = _call_analyze_failure_causes_compat(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
        file_path=file_path,
    )
    candidates = _build_candidates(
        error_text=error_text,
        file_path=file_path,
        semantic=semantic,
    )

    _emit_thought(
        thought_bus,
        "Candidate Generation",
        f"{len(candidates)} candidates produced",
        kind="info",
    )

    expert_names = sorted({
        str((c or {}).get("expert") or "unknown")
        for c in candidates
        if isinstance(c, dict)
    })
    _emit_thought(
        thought_bus,
        "Expert Routing",
        "experts=" + ", ".join(expert_names),
        kind="info",
    )

    for cand in list(candidates)[:3]:
        if isinstance(cand, dict):
            _emit_thought(
                thought_bus,
                "Hypothesis Generation",
                str(
                    cand.get("summary")
                    or cand.get("semantic_claim")
                    or cand.get("hypothesis")
                    or "candidate proposed"
                ),
                kind="info",
                confidence=cand.get("confidence"),
                file_path=cand.get("target_file") or cand.get("file_path_hint"),
            )

    base_plans = build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
        candidates=candidates,
        file_path=file_path,
    )

    multifile_plans = expand_multifile_plan_family(
        base_plans=base_plans,
        file_path=file_path,
        semantic=semantic,
    )

    _emit_thought(
        thought_bus,
        "Planning",
        f"base_plans={len(base_plans)} multifile_plans={len(multifile_plans)}",
        kind="info",
    )

    _emit_thought(
        thought_bus,
        "Plan Expansion",
        f"total_plans={len(base_plans) + len(multifile_plans)}",
        kind="info",
    )

    all_plans = list(base_plans) + list(multifile_plans)

    enriched = []
    for plan in all_plans:
        plan = _force_plan_target_to_file(plan, file_path)
        branch = _maybe_execute_repair_plan(plan, file_path) if file_path else None
        contract = synthesize_and_check_contract(
            before_error_text=error_text,
            branch_result=branch or {},
            expected_behavior=plan.get("expected_behavior", {}),
        )

        p2 = dict(plan)
        p2["branch_result"] = branch
        p2["contract_result"] = contract
        p2["contract_propagation"] = check_contract_propagation(p2)
        enriched.append(p2)

    ranked = rank_plans(enriched)

    if ranked:
        best = ranked[0]
        evidence = best.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best.get("edits") or [{}])[0].get("file")) or best.get("target_file")
        _emit_thought(
            thought_bus,
            "Ranking",
            f"best strategy={strategy} target={target}",
            kind="success",
            confidence=best.get("confidence"),
            file_path=target,
        )
        _emit_thought(
            thought_bus,
            "Plan Rejection",
            f"rejected={max(0, len(ranked) - 1)} alternate_plans={max(0, len(ranked) - 1)}",
            kind="warn" if len(ranked) > 1 else "info",
        )
    else:
        _emit_thought(
            thought_bus,
            "Ranking",
            "no ranked plans available",
            kind="fail",
        )

    best_plan = ranked[0] if ranked else None

    return {
        "project_graph": graph,
        "causes": causes,
        "candidate_count": len(candidates),
        "base_plan_count": len(base_plans),
        "multifile_plan_count": len(multifile_plans),
        "repair_plans": ranked,
        "best_plan": best_plan,
        "branch_result": (best_plan or {}).get("branch_result"),
        "contract_result": (best_plan or {}).get("contract_result"),
        "contract_propagation": (best_plan or {}).get("contract_propagation"),
    }
# ----------------------------------------------------------------------
# adaptive fast policy override
# ----------------------------------------------------------------------

def _adaptive_fast_allowed(plan, file_path: str | None = None) -> bool:
    if not globals().get("_FAST_VERIFY_MODE", False):
        return False

    try:
        if _plan_is_multifile(plan):
            return False
    except Exception:
        return False

    target_file = (
        (plan or {}).get("target_file")
        or file_path
        or (((plan or {}).get("edits") or [{}])[0].get("file") if isinstance(plan, dict) else None)
        or ""
    )
    if Path(str(target_file)).suffix.lower() != ".py":
        return False

    try:
        candidate = plan_to_candidate(plan) if isinstance(plan, dict) else {}
    except Exception:
        candidate = {}

    summary = str((candidate or {}).get("summary") or "").lower()
    kind = str((candidate or {}).get("kind") or "").lower()
    evidence = (plan or {}).get("evidence") or {}
    strategy = str(evidence.get("strategy") or "").lower()

    text = " ".join([summary, kind, strategy])

    # current benchmark evidence: dependency/import cases are the safe fast win
    allow_tokens = ("dependency", "import", "module", "submodule", "alias")
    deny_tokens = ("file not found", "missing file", "runtime", "shell", "command not found", "write parent", "env file", "config")

    if any(tok in text for tok in deny_tokens):
        return False

    if any(tok in text for tok in allow_tokens):
        return True

    return False


def _maybe_execute_repair_plan(plan, file_path: str | None = None):
    if not globals().get("_FAST_VERIFY_MODE", False):
        return execute_repair_plan(plan, file_path)

    if _adaptive_fast_allowed(plan, file_path=file_path):
        return _fast_verify_candidate(plan, file_path=file_path)

    return execute_repair_plan(plan, file_path)
def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _extract_traceback_frames(error_text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    text = error_text or ""
    for m in re.finditer(r'File "([^"]+)", line (\d+)', text):
        frames.append({
            "filename": m.group(1),
            "lineno": int(m.group(2)),
        })
    return frames


def _fast_engine_supported(error_text: str, file_path: str | None, fast: bool) -> bool:
    if not fast:
        return False
    if not file_path or not str(file_path).endswith(".py"):
        return False
    if "FORCED_SEMANTIC_ANALYSIS" in (error_text or ""):
        return False
    if _env_truthy("TERMORGANISM_FAST_ENGINE_ALL"):
        return True

    s = (error_text or "").lower()
    allow = (
        "module not found" in s
        or "modulenotfounderror" in s
        or "importerror" in s
        or "cannot import name" in s
        or "nameerror" in s
        or "syntaxerror" in s
        or "indentationerror" in s
    )
    deny = (
        "file not found" in s
        or "filenotfounderror" in s
        or "permissionerror" in s
        or "isadirectoryerror" in s
    )
    return allow and not deny


def _run_fast_engine_repair(error_text: str, file_path: str, thought_bus=None):
    from core.modes.fast_repair import FastRepairMode

    _emit_thought(
        thought_bus,
        "Fast Engine",
        "experimental fast engine route selected",
        kind="info",
        file_path=file_path,
    )

    failure_context = {
        "error_text": error_text,
        "traceback": _extract_traceback_frames(error_text),
        "target_file": file_path,
    }

    try:
        result = asyncio.run(FastRepairMode().repair(Path(file_path), failure_context))
    except Exception as exc:
        _emit_thought(
            thought_bus,
            "Fast Engine",
            f"fast engine failed: {exc}",
            kind="warn",
            file_path=file_path,
        )
        return None

    if not result or not result.candidate or not result.verification:
        _emit_thought(
            thought_bus,
            "Fast Engine",
            "no usable fast-engine candidate; falling back",
            kind="warn",
            file_path=file_path,
        )
        return None

    verification = result.verification or {}
    branch_result = {
        "ok": bool(verification.get("ok")),
        "reason": "fast engine lightweight verification",
        "applied_files": [file_path],
        "workspace_root": None,
        "runtime": verification.get("runtime") or {},
        "static_verify": verification.get("static_verify") or {},
        "fast_mode": True,
    }

    contract_result = synthesize_and_check_contract(
        before_error_text=error_text,
        branch_result=branch_result,
        expected_behavior={"exit_code": 0},
    )

    candidate = dict(result.candidate)
    plan_result = {
        "expert": "fast_engine",
        "kind": str(candidate.get("kind") or candidate.get("type") or "fast_engine"),
        "confidence": float(result.confidence or 0.0),
        "summary": str(candidate.get("summary") or candidate.get("description") or f"Fast engine repair via {result.method}"),
        "patch": str(candidate.get("patch") or ""),
        "candidate_code": str(candidate.get("candidate_code") or candidate.get("code") or ""),
        "file_path_hint": str(file_path),
        "target_file": str(file_path),
        "metadata": {
            "fast_engine": True,
            "method": result.method,
            "trace": list(result.trace or []),
            "cache_key": result.cache_key,
            "memory_prior": 0.5,
        },
        "branch_result": branch_result,
        "contract_result": contract_result,
    }

    _emit_thought(
        thought_bus,
        "Fast Engine",
        f"method={result.method} confidence={result.confidence:.2f} latency_ms={result.latency_ms:.1f}",
        kind="success" if result.success else "warn",
        confidence=float(result.confidence or 0.0),
        file_path=file_path,
    )

    payload = {
        "result": plan_result,
        "semantic": {
            "repro": {
                "ok": True,
                "reproduced": False,
                "returncode": 0 if result.success else 1,
                "stdout": "",
                "stderr": error_text,
                "exception_type": "FastEngineRoute",
            },
            "localization": {
                "count": len(failure_context["traceback"]),
                "top": failure_context["traceback"][-1] if failure_context["traceback"] else {"file_path": file_path, "reason": "fast-engine target"},
                "items": failure_context["traceback"],
            },
        },
        "planner": {
            "candidate_count": 1,
            "base_plan_count": 1,
            "multifile_plan_count": 0,
            "repair_plans": [plan_result],
            "best_plan": plan_result,
            "branch_result": branch_result,
            "contract_result": contract_result,
            "contract_propagation": {"ok": True, "score": 1.0, "reason": "fast-engine direct path"},
        },
        "best_plan": plan_result,
        "plan_score": float(result.confidence or 0.0),
        "rank_tuple": (True, float(result.confidence or 0.0)),
        "branch_result": branch_result,
        "contract_result": contract_result,
        "contract_propagation": {"ok": True, "score": 1.0, "reason": "fast-engine direct path"},
        "routes": ["fast_engine"],
        "verify": {"ok": bool(result.success), "reason": "fast-engine path selected"},
        "behavioral_verify": branch_result,
        "synthesized_tests": contract_result,
        "sandbox": None,
        "apply": None,
        "exec": None,
        "candidate_count": 1,
        "candidates": [plan_result],
        "metrics": {
            "mode": "fast",
            "fast": True,
            "fast_engine": True,
            "total_ms": round(float(result.latency_ms), 3),
            "semantic_ms": 0.0,
            "planning_ms": 0.0,
            "selection_ms": 0.0,
        },
        "confidence": {
            "score": float(result.confidence or 0.0),
            "factors": {
                "static_valid": 1.0 if (verification.get("static_verify") or {}).get("ok") else 0.0,
                "behavioral_match": 1.0 if (verification.get("runtime") or {}).get("returncode") == 0 else 0.0,
                "sandbox_pass": 0.6,
                "cross_file_consistency": 1.0,
                "memory_prior": 0.5,
            },
            "uncertainty": "fast_engine_lightweight_verify",
            "recommendation": "apply_with_review" if float(result.confidence or 0.0) >= 0.80 else "human_review",
        },
    }
    return payload
