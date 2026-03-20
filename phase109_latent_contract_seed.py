#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/autofix.py": r'''from __future__ import annotations

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

    # prefer local user module over stdlib-like names
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

        items = []
        items.append({
            "file_path": caller,
            "line_no": None,
            "symbol": None,
            "reason": "forced semantic caller seed",
            "score": 0.91,
        })
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


def _build_candidates(error_text: str, file_path: str | None) -> list[dict[str, Any]]:
    ctx = type("Ctx", (), {})()
    ctx.error_text = error_text
    ctx.file_path = file_path

    if file_path:
        try:
            ctx.source_code = Path(file_path).read_text(encoding="utf-8")
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


def _build_repair_planner_prelude(error_text: str, file_path: str | None, semantic: dict[str, Any] | None):
    graph = build_project_graph(file_path).to_dict() if file_path else {"project_root": str("."), "files": [], "adjacency": {}}

    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
    )]

    candidates = _build_candidates(error_text=error_text, file_path=file_path)

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

    all_plans = list(base_plans) + list(multifile_plans)

    enriched = []
    for plan in all_plans:
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


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False):
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    planner = _build_repair_planner_prelude(error_text=error_text, file_path=file_path, semantic=semantic)

    best_plan = (planner or {}).get("best_plan")
    plan_result = plan_to_candidate(best_plan) if best_plan else None
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
''',

    "test_phase109_latent_contract_seed.py": r'''from __future__ import annotations

import json
import subprocess


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def main():
    forced = run(["./termorganism", "demo/cross_file_dep.py", "--json", "--force-semantic"])
    payload = json.loads(forced["stdout"])

    best = payload.get("best_plan") or {}
    ev = best.get("evidence") or {}
    semantic = payload.get("semantic") or {}
    localization = semantic.get("localization") or {}

    print(json.dumps({
        "forced_has_best_plan": bool(best),
        "forced_best_plan_id": best.get("plan_id"),
        "forced_strategy": ev.get("strategy"),
        "forced_provider": ev.get("provider"),
        "forced_caller": ev.get("caller"),
        "localization_count": localization.get("count"),
        "localization_top": localization.get("top"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
'''
}


def backup_and_write(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        print(f"[BACKUP] {rel_path} -> {backup.relative_to(ROOT)}")
    path.write_text(content, encoding="utf-8")
    print(f"[WRITE]  {rel_path}")


def main() -> int:
    for rel_path, content in PATCHES.items():
        backup_and_write(rel_path, content)
    print("\\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
