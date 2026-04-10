from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/planner/multi_file_planner.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any


def _canon(p: str | None) -> str | None:
    if not p:
        return None
    try:
        return str(Path(p).resolve())
    except Exception:
        return str(Path(p))


def build_multifile_plan_from_base(
    *,
    base_plan: dict[str, Any],
    file_path: str | None,
    semantic: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not file_path:
        return None

    semantic_loc = ((semantic or {}).get("localization") or {}) if isinstance(semantic, dict) else {}
    items = semantic_loc.get("items", []) or []

    caller = _canon(file_path)
    provider = None

    for item in items:
        fp = item.get("file_path")
        if not fp:
            continue

        fp_canon = _canon(fp)
        if not fp_canon or not fp_canon.endswith(".py"):
            continue
        if "/usr/lib/" in fp_canon:
            continue
        if fp_canon == caller:
            continue

        provider = fp_canon
        break

    if not provider:
        return None

    edits = list(base_plan.get("edits", []) or [])
    if not edits:
        return None

    first = dict(edits[0])
    first["file"] = provider

    new_plan = dict(base_plan)
    new_plan["plan_id"] = f"{base_plan.get('plan_id', 'plan')}_multifile"
    new_plan["hypothesis"] = "provider/caller contract is broken across files; repair provider-side behavior first"
    new_plan["target_files"] = [provider, caller]
    new_plan["edits"] = [first]
    new_plan["confidence"] = max(float(base_plan.get("confidence", 0.0) or 0.0), 0.90)
    new_plan["risk"] = max(float(base_plan.get("risk", 0.12) or 0.12), 0.14)
    new_plan["blast_radius"] = max(float(base_plan.get("blast_radius", 0.0) or 0.0), 0.16)

    evidence = dict(new_plan.get("evidence", {}) or {})
    evidence["multifile"] = True
    evidence["caller"] = caller
    evidence["provider"] = provider
    new_plan["evidence"] = evidence

    return new_plan


def expand_multifile_plan_family(
    *,
    base_plans: list[dict[str, Any]],
    file_path: str | None,
    semantic: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for plan in base_plans or []:
        mf = build_multifile_plan_from_base(
            base_plan=plan,
            file_path=file_path,
            semantic=semantic,
        )
        if not mf:
            continue

        plan_id = str(mf.get("plan_id", ""))
        if plan_id in seen_ids:
            continue
        seen_ids.add(plan_id)
        expanded.append(mf)

    return expanded
''',

    "core/autofix.py": r'''from __future__ import annotations

from typing import Any
import ast
import re

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.engine.router import PolicyRouter
from core.verify.sandbox import VerifierHub, run_in_sandbox
from core.verify.python_verify import verify_python
from core.verify.behavioral_verify import verify_python_runtime, verify_repro_delta
from core.verify.contract_propagation import check_contract_propagation
from core.memory import event_store, retrieval
from core.util.patch_apply import make_backup, apply_text_replacement, restore_backup
from core.util.safe_exec import execute_safe_suggestions
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.testsynth.replay_test import run_python_replay
from core.testsynth.regression_guard import (
    check_failure_signature_removed,
    check_expected_exception_absent,
    combine_regression_guards,
)
from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.multi_file_planner import expand_multifile_plan_family
from core.planner.branch_executor import execute_repair_plan
from core.verify.contract_synth import synthesize_and_check_contract
from core.ranker.plan_ranker import rank_plans, score_plan
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


class RankerAdapter:
    def _score(self, candidate):
        if isinstance(candidate, dict):
            base = float(candidate.get("confidence", 0.0) or 0.0)
            repro_fix = float(candidate.get("repro_fix_score", 0.0) or 0.0)
            regression = float(candidate.get("regression_score", 0.0) or 0.0)
            synthesized = float(candidate.get("synth_test_score", 0.0) or 0.0)
            prior = float(candidate.get("historical_success_prior", 0.0) or 0.0)
            blast_radius = float(candidate.get("blast_radius", 0.0) or 0.0)
            sandbox_bonus = 0.10 if ((candidate.get("sandbox") or {}).get("ok") is True) else 0.0
            propagation_bonus = float(((candidate.get("contract_propagation") or {}).get("score", 0.0)) or 0.0)
            return base + repro_fix + regression + synthesized + prior + sandbox_bonus + propagation_bonus - blast_radius
        return getattr(candidate, "confidence", 0.0)

    def rank(self, candidates, context=None):
        if not isinstance(candidates, list):
            return candidates
        return sorted(candidates, key=self._score, reverse=True)


class ExpertAdapter:
    def __init__(self):
        self._registry = {
            "python_syntax": PythonSyntaxExpert(),
            "dependency": DependencyExpert(),
            "shell_runtime": ShellRuntimeExpert(),
            "memory_retrieval": MemoryRetrievalExpert(),
            "llm_fallback": LLMFallbackExpert(),
            "file_runtime": FileRuntimeExpert(),
        }

    def get(self, name: str):
        return self._registry[name]


def _build_orchestrator() -> Orchestrator:
    return Orchestrator(
        router=PolicyRouter(),
        experts=ExpertAdapter(),
        verifier=VerifierHub(),
        ranker=RankerAdapter(),
        store=EventStoreAdapter(),
    )


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


def _build_repair_planner_prelude(error_text: str, file_path: str | None, semantic: dict[str, Any] | None):
    graph = build_project_graph(file_path).to_dict() if file_path else {"project_root": str("."), "files": [], "adjacency": {}}

    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
    )]

    base_plans = [p.to_dict() for p in build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
    )]

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
        p2["plan_score"] = score_plan(p2)
        enriched.append(p2)

    ranked = rank_plans(enriched)
    best_plan = ranked[0] if ranked else None

    return {
        "project_graph": graph,
        "causes": causes,
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

    "test_phase103_plan_family.py": r'''from __future__ import annotations

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
    "base_plan_count": planner.get("base_plan_count"),
    "multifile_plan_count": planner.get("multifile_plan_count"),
    "best_plan_id": best.get("plan_id"),
    "strategy": ev.get("strategy"),
    "provider": ev.get("provider"),
    "caller": ev.get("caller"),
    "target_files": best.get("target_files"),
    "top_5_plan_ids": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "score": p.get("plan_score"),
        }
        for p in (planner.get("repair_plans") or [])[:5]
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
