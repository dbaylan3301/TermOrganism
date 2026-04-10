from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/ranker/plan_ranker.py": r'''from __future__ import annotations

from typing import Any


def _strategy_semantic_weight(strategy: str) -> float:
    strategy = str(strategy or "")
    if strategy == "guard_exists":
        return 1.00
    if strategy == "try_except_recovery":
        return 0.72
    if strategy == "touch_only":
        return 0.18
    return 0.40


def _infer_strategy(plan: dict[str, Any]) -> str:
    evidence = plan.get("evidence", {}) or {}
    strategy = str(evidence.get("strategy", "") or "").strip()
    if strategy:
        return strategy

    edits = plan.get("edits", []) or []
    if edits:
        first = edits[0]
        kind = str(first.get("kind", "") or "")
        code = str(first.get("candidate_code", "") or "")

        if kind == "operational":
            return "touch_only"
        if 'exists() else ""' in code:
            return "guard_exists"
        if "except FileNotFoundError" in code:
            return "try_except_recovery"

    summary = " ".join(
        str(x or "") for x in [
            plan.get("hypothesis", ""),
            *((e.get("summary", "") for e in edits)),
        ]
    )

    if "exists" in summary:
        return "guard_exists"
    if "FileNotFoundError" in summary or "exception" in summary:
        return "try_except_recovery"
    return "unknown"


def _has_code_edit(plan: dict[str, Any]) -> bool:
    for edit in plan.get("edits", []) or []:
        if edit.get("kind") == "replace_full" and (edit.get("candidate_code", "") or "").strip():
            return True
    return False


def _rank_tuple(plan: dict[str, Any]):
    evidence = dict(plan.get("evidence", {}) or {})
    strategy = _infer_strategy(plan)
    evidence["strategy"] = strategy
    plan["evidence"] = evidence

    confidence = float(plan.get("confidence", 0.0) or 0.0)
    risk = float(plan.get("risk", 0.0) or 0.0)
    blast_radius = float(plan.get("blast_radius", 0.0) or 0.0)

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}

    has_code = _has_code_edit(plan)
    multifile = evidence.get("multifile") is True

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_score = float(contract.get("score", 0.0) or 0.0)
    propagation_score = float(propagation.get("score", 0.0) or 0.0)
    semantic_bonus = _strategy_semantic_weight(strategy) * 0.90
    multifile_bonus = 0.20 if multifile else 0.0
    code_bonus = 0.35 if has_code else -0.45

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    final_score = (
        confidence
        + branch_bonus
        + contract_score
        + propagation_score
        + semantic_bonus
        + multifile_bonus
        + code_bonus
        - risk
        - blast_radius
        - complexity_penalty
    )

    semantic_priority = {
        "guard_exists": 3,
        "try_except_recovery": 2,
        "touch_only": 1,
        "unknown": 0,
    }.get(strategy, 0)

    # single source of truth
    return (
        has_code,
        contract_score,
        propagation_score,
        semantic_priority,
        round(final_score, 6),
    )


def score_plan(plan: dict[str, Any]) -> float:
    return float(_rank_tuple(plan)[-1])


def annotate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    rt = _rank_tuple(plan)
    evidence = dict(plan.get("evidence", {}) or {})
    out = dict(plan)
    out["evidence"] = evidence
    out["rank_tuple"] = list(rt)
    out["plan_score"] = float(rt[-1])
    return out


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = [annotate_plan(dict(p)) for p in (plans or [])]
    annotated.sort(key=lambda p: tuple(p.get("rank_tuple", [])), reverse=True)
    return annotated
''',

    "core/autofix.py": r'''from __future__ import annotations

from typing import Any
from pathlib import Path

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


def _build_semantic_prelude(error_text: str, file_path: str | None):
    if file_path and str(file_path).endswith(".py"):
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
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

    "test_phase105_unified_truth.py": r'''from __future__ import annotations

import json
from core.autofix import run_autofix

error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

res = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

planner = res.get("planner") or {}
best = res.get("best_plan") or {}
ev = best.get("evidence") or {}

print(json.dumps({
    "best_plan_id": best.get("plan_id"),
    "strategy": ev.get("strategy"),
    "plan_score": best.get("plan_score"),
    "rank_tuple": best.get("rank_tuple"),
    "provider": ev.get("provider"),
    "caller": ev.get("caller"),
    "top_8": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "plan_score": p.get("plan_score"),
            "rank_tuple": p.get("rank_tuple"),
        }
        for p in (planner.get("repair_plans") or [])[:8]
    ],
}, indent=2, ensure_ascii=False))
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
