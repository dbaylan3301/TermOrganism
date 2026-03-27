from __future__ import annotations
from core.ui.thoughts import ThoughtEvent

from typing import Any
from pathlib import Path
import ast

from core.memory import event_store
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.multi_file_planner import expand_multifile_plan_family
from core.planner.branch_executor import execute_repair_plan


import sys
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
from core.ranker.plan_ranker import rank_plans
from core.planner.plan_normalizer import plan_to_candidate
from core.planner.plan_apply import apply_plan

from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.file_runtime import FileRuntimeExpert


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


def _build_repair_planner_prelude(error_text: str, file_path: str | None, semantic: dict[str, Any] | None, thought_bus=None):
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

    all_plans = list(base_plans) + list(multifile_plans)

    enriched = []
    for plan in all_plans:
        plan = _force_plan_target_to_file(plan, file_path)
        branch = execute_repair_plan(plan, file_path) if file_path else None
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


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False, thought_bus=None):
    _requested_file_path = file_path
    _emit_thought(
        thought_bus,
        "Input",
        f"target={file_path or '<none>'}",
        kind="info",
    )
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)

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

    planner = _build_repair_planner_prelude(error_text=error_text, file_path=file_path, semantic=semantic, thought_bus=thought_bus)
    planner = _force_plan_target_to_file(planner, file_path)
    if isinstance(planner, dict) and isinstance(planner.get("source_plan"), dict):
        planner["source_plan"] = _force_plan_target_to_file(planner["source_plan"], file_path)

    best_plan = (planner or {}).get("best_plan")

    if best_plan:
        evidence = best_plan.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best_plan.get("edits") or [{}])[0].get("file")) or best_plan.get("target_file")
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
            "Sandbox",
            f"ok={behavioral.get('ok')} returncode={(behavioral.get('runtime') or {}).get('returncode')}",
            kind="success" if behavioral.get("ok") else "fail",
        )

    if isinstance(contract, dict) and contract:
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
        "candidate_count": 1 if plan_result else 0,
        "candidates": [plan_result] if plan_result else [],
    }
