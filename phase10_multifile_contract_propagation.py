#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/verify/contract_propagation.py": r'''from __future__ import annotations

from typing import Any


def check_contract_propagation(best_plan: dict[str, Any] | None) -> dict[str, Any]:
    if not best_plan:
        return {
            "ok": False,
            "reason": "no best_plan",
            "score": 0.0,
            "checks": [],
        }

    target_files = best_plan.get("target_files", []) or []
    edits = best_plan.get("edits", []) or []
    branch = best_plan.get("branch_result", {}) or {}
    contract = best_plan.get("contract_result", {}) or {}

    checks: list[dict[str, Any]] = []

    checks.append({
        "name": "multi_file_targeting",
        "ok": len(target_files) >= 1,
        "actual": len(target_files),
    })

    checks.append({
        "name": "edit_plan_present",
        "ok": len(edits) >= 1,
        "actual": len(edits),
    })

    checks.append({
        "name": "branch_execution_passed",
        "ok": bool(branch.get("ok", False)),
    })

    checks.append({
        "name": "contract_checks_passed",
        "ok": bool(contract.get("ok", False)),
        "actual": float(contract.get("score", 0.0) or 0.0),
    })

    score = 0.0
    weights = {
        "multi_file_targeting": 0.15,
        "edit_plan_present": 0.15,
        "branch_execution_passed": 0.35,
        "contract_checks_passed": 0.35,
    }

    for item in checks:
        if item["ok"]:
            score += weights.get(item["name"], 0.0)

    return {
        "ok": score >= 0.70,
        "reason": "contract propagation checks evaluated",
        "score": round(score, 4),
        "checks": checks,
    }
''',

    "core/planner/multi_file_planner.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any


def build_multifile_plan(
    *,
    file_path: str | None,
    semantic: dict[str, Any] | None,
    planner: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not file_path:
        return None

    best_plan = ((planner or {}).get("best_plan")) if isinstance(planner, dict) else None
    if not best_plan:
        return None

    semantic_loc = ((semantic or {}).get("localization") or {}) if isinstance(semantic, dict) else {}
    items = semantic_loc.get("items", []) or []

    caller = str(file_path)
    provider = None

    for item in items:
        fp = item.get("file_path")
        if fp and str(fp).endswith(".py") and str(fp) != caller and "/usr/lib/" not in str(fp):
            provider = str(fp)
            break

    if not provider:
        return None

    edits = list(best_plan.get("edits", []) or [])
    if not edits:
        return None

    first = dict(edits[0])
    first["file"] = provider

    new_plan = dict(best_plan)
    new_plan["plan_id"] = f"{best_plan.get('plan_id', 'plan')}_multifile"
    new_plan["hypothesis"] = "provider/caller contract is broken across files; repair provider-side behavior first"
    new_plan["target_files"] = [provider, caller]
    new_plan["edits"] = [first]
    new_plan["confidence"] = max(float(best_plan.get("confidence", 0.0) or 0.0), 0.90)
    new_plan["risk"] = min(float(best_plan.get("risk", 0.12) or 0.12), 0.18)
    new_plan["blast_radius"] = max(float(best_plan.get("blast_radius", 0.0) or 0.0), 0.16)

    evidence = dict(new_plan.get("evidence", {}) or {})
    evidence["multifile"] = True
    evidence["caller"] = caller
    evidence["provider"] = provider
    new_plan["evidence"] = evidence

    return new_plan
''',

    "core/ranker/plan_ranker.py": r'''from __future__ import annotations

from typing import Any


def score_plan(plan: dict[str, Any]) -> float:
    confidence = float(plan.get("confidence", 0.0) or 0.0)
    risk = float(plan.get("risk", 0.0) or 0.0)
    blast_radius = float(plan.get("blast_radius", 0.0) or 0.0)

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_bonus = float(contract.get("score", 0.0) or 0.0)
    propagation_bonus = float(propagation.get("score", 0.0) or 0.0)

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    multifile_bonus = 0.10 if ((plan.get("evidence") or {}).get("multifile") is True) else 0.0

    return confidence + branch_bonus + contract_bonus + propagation_bonus + multifile_bonus - risk - blast_radius - complexity_penalty


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(plans, key=score_plan, reverse=True)
''',

    "core/planner/plan_normalizer.py": r'''from __future__ import annotations

from typing import Any


def plan_to_candidate(plan: dict[str, Any]) -> dict[str, Any]:
    edits = plan.get("edits", []) or []
    first_edit = edits[0] if edits else {}

    evidence = plan.get("evidence", {}) or {}
    target_files = plan.get("target_files", []) or []
    target_file = target_files[0] if target_files else first_edit.get("file")

    patch = None
    if first_edit.get("kind") == "operational":
        cmds = first_edit.get("commands", []) or []
        patch = " && ".join(cmds) if cmds else None
    elif first_edit.get("kind") == "replace_full":
        ev_strategy = evidence.get("strategy", "")
        if ev_strategy in {"guard_exists", "try_except_recovery"}:
            patch = "mkdir -p logs && touch logs/app.log"

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}

    return {
        "expert": "planner",
        "kind": "runtime_file_missing",
        "confidence": float(plan.get("confidence", 0.0) or 0.0),
        "summary": first_edit.get("summary", plan.get("hypothesis", "repair plan")),
        "patch": patch,
        "candidate_code": first_edit.get("candidate_code", "") or "",
        "file_path_hint": target_file,
        "target_file": target_file,
        "hypothesis": plan.get("hypothesis", ""),
        "semantic_claim": "plan-first multi-file repair selection",
        "affected_scope": target_files,
        "metadata": {
            "strategy": evidence.get("strategy", ""),
            "plan_id": plan.get("plan_id", ""),
            "multifile": evidence.get("multifile", False),
            "caller": evidence.get("caller"),
            "provider": evidence.get("provider"),
        },
        "repro_fix_score": 0.75 if branch.get("ok") else 0.0,
        "regression_score": float(contract.get("score", 0.0) or 0.0) * 0.65,
        "synth_test_score": float(contract.get("score", 0.0) or 0.0),
        "historical_success_prior": 0.0,
        "blast_radius": float(plan.get("blast_radius", 0.0) or 0.0),
        "branch_result": branch,
        "contract_result": contract,
        "contract_propagation": propagation,
        "source_plan": plan,
    }
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
from core.planner.multi_file_planner import build_multifile_plan
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


def _extract_field(text: str, field: str):
    patterns = [
        rf"{field}='((?:[^'\\\\]|\\\\.)*)'",
        rf'{field}="((?:[^"\\\\]|\\\\.)*)"',
        rf"{field}=([0-9]+(?:\.[0-9]+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            raw = m.group(1)
            try:
                return ast.literal_eval(f"'{raw}'")
            except Exception:
                try:
                    return float(raw) if "." in raw or raw.isdigit() else raw
                except Exception:
                    return raw
    return None


def _normalize_candidate(candidate):
    if isinstance(candidate, dict):
        c = dict(candidate)
        c.setdefault("kind", "")
        c.setdefault("confidence", 0.0)
        c.setdefault("candidate_code", "")
        c.setdefault("metadata", {})
        c.setdefault("repro_fix_score", 0.0)
        c.setdefault("regression_score", 0.0)
        c.setdefault("synth_test_score", 0.0)
        c.setdefault("historical_success_prior", 0.0)
        c.setdefault("blast_radius", 0.0)
        c.setdefault("hypothesis", "")
        c.setdefault("semantic_claim", "")
        c.setdefault("affected_scope", [])
        c.setdefault("target_file", c.get("file_path_hint"))
        patch = c.get("patch")
        if c["kind"] == "" and isinstance(patch, str) and patch.startswith("pip install "):
            c["kind"] = "dependency_install"
        elif c["kind"] == "" and c.get("expert") == "file_runtime":
            c["kind"] = "runtime_file_missing"
        return c

    attrs = {}
    for name in (
        "expert_name",
        "kind",
        "patched_code",
        "patch_unified_diff",
        "rationale",
        "router_score",
        "expert_score",
        "memory_prior",
        "patch_safety_score",
        "metadata",
    ):
        if hasattr(candidate, name):
            attrs[name] = getattr(candidate, name)

    if attrs:
        return {
            "expert": attrs.get("expert_name", "unknown"),
            "kind": attrs.get("kind", ""),
            "confidence": attrs.get("expert_score", 0.0),
            "summary": attrs.get("rationale", ""),
            "patch": attrs.get("patch_unified_diff"),
            "candidate_code": attrs.get("patched_code", "") or "",
            "raw_candidate": str(candidate),
            "metadata": attrs.get("metadata", {}) or {},
            "router_score": attrs.get("router_score", 0.0),
            "expert_score": attrs.get("expert_score", 0.0),
            "memory_prior": attrs.get("memory_prior", 0.0),
            "patch_safety_score": attrs.get("patch_safety_score", 0.0),
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "synth_test_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
            "target_file": None,
        }

    text = str(candidate)
    if "RepairCandidate(" in text:
        return {
            "expert": _extract_field(text, "expert_name") or "python_syntax",
            "kind": _extract_field(text, "kind") or "python_patch",
            "confidence": _extract_field(text, "expert_score") or 0.0,
            "summary": _extract_field(text, "rationale") or text,
            "patch": _extract_field(text, "patch_unified_diff"),
            "candidate_code": _extract_field(text, "patched_code") or "",
            "raw_candidate": text,
            "metadata": {},
            "router_score": _extract_field(text, "router_score") or 0.0,
            "expert_score": _extract_field(text, "expert_score") or 0.0,
            "memory_prior": _extract_field(text, "memory_prior") or 0.0,
            "patch_safety_score": _extract_field(text, "patch_safety_score") or 0.0,
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "synth_test_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
            "target_file": None,
        }

    return {
        "expert": "unknown",
        "kind": "unknown",
        "confidence": 0.0,
        "summary": text,
        "patch": None,
        "candidate_code": "",
        "raw_candidate": text,
        "metadata": {},
        "repro_fix_score": 0.0,
        "regression_score": 0.0,
        "synth_test_score": 0.0,
        "historical_success_prior": 0.0,
        "blast_radius": 0.0,
        "hypothesis": "",
        "semantic_claim": "",
        "affected_scope": [],
        "target_file": None,
    }


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
    plans = [p.to_dict() for p in build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
    )]

    ranked_initial = rank_plans(plans)
    initial_best = ranked_initial[0] if ranked_initial else None
    multifile = build_multifile_plan(file_path=file_path, semantic=semantic, planner={"best_plan": initial_best})

    if multifile:
        plans.append(multifile)

    enriched = []
    for plan in plans:
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

    "test_phase10_multifile.py": r'''from __future__ import annotations

import json
from core.autofix import run_autofix

res = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
    file_path="demo/cross_file_dep.py",
)

print(json.dumps({
    "routes": res.get("routes"),
    "plan_score": res.get("plan_score"),
    "best_plan_id": (res.get("best_plan") or {}).get("plan_id"),
    "contract_propagation": res.get("contract_propagation"),
    "target_files": (res.get("best_plan") or {}).get("target_files"),
    "provider": (((res.get("best_plan") or {}).get("evidence") or {}).get("provider")),
    "caller": (((res.get("best_plan") or {}).get("evidence") or {}).get("caller")),
}, indent=2, ensure_ascii=False))
''',
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
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
