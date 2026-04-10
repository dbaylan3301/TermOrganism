from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/ranker/plan_ranker.py": r'''from __future__ import annotations

from typing import Any


def score_plan(plan: dict[str, Any]) -> float:
    confidence = float(plan.get("confidence", 0.0) or 0.0)
    risk = float(plan.get("risk", 0.0) or 0.0)
    blast_radius = float(plan.get("blast_radius", 0.0) or 0.0)

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_bonus = float(contract.get("score", 0.0) or 0.0)

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    return confidence + branch_bonus + contract_bonus - risk - blast_radius - complexity_penalty


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
        "semantic_claim": "plan-first repair selection",
        "affected_scope": target_files,
        "metadata": {
            "strategy": evidence.get("strategy", ""),
            "plan_id": plan.get("plan_id", ""),
        },
        "repro_fix_score": 0.75 if branch.get("ok") else 0.0,
        "regression_score": float(contract.get("score", 0.0) or 0.0) * 0.65,
        "synth_test_score": float(contract.get("score", 0.0) or 0.0),
        "historical_success_prior": 0.0,
        "blast_radius": float(plan.get("blast_radius", 0.0) or 0.0),
        "branch_result": branch,
        "contract_result": contract,
        "source_plan": plan,
    }
''',

    "core/planner/edit_ops.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any


def apply_edit(edit: dict[str, Any]) -> dict[str, Any]:
    file_path = edit.get("file")
    if not file_path:
        return {"ok": False, "reason": "missing edit file"}

    p = Path(file_path)
    kind = edit.get("kind", "")

    if kind == "replace_full":
        code = edit.get("candidate_code", "") or ""
        if not code.strip():
            return {"ok": False, "reason": "empty candidate_code"}
        p.write_text(code, encoding="utf-8")
        return {"ok": True, "reason": "replace_full applied", "file": str(p)}

    if kind == "operational":
        for cmd in edit.get("commands", []) or []:
            if cmd.startswith("mkdir -p "):
                folder = cmd[len("mkdir -p "):].strip()
                Path(folder).mkdir(parents=True, exist_ok=True)
            elif cmd.startswith("touch "):
                target = Path(cmd[len("touch "):].strip())
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
        return {"ok": True, "reason": "operational edit applied", "file": str(p)}

    return {"ok": False, "reason": f"unsupported edit kind: {kind}"}
''',

    "core/planner/plan_apply.py": r'''from __future__ import annotations

from pathlib import Path
from typing import Any

from core.util.patch_apply import make_backup
from core.planner.edit_ops import apply_edit
from core.verify.python_verify import verify_python


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    edits = plan.get("edits", []) or []
    backups: list[str] = []
    applied: list[dict[str, Any]] = []

    for edit in edits:
        file_path = edit.get("file")
        if file_path and Path(file_path).exists():
            backups.append(str(make_backup(file_path)))

        res = apply_edit(edit)
        applied.append(res)
        if not res.get("ok"):
            return {
                "applied": False,
                "reason": res.get("reason", "edit failed"),
                "backups": backups,
                "results": applied,
            }

        if edit.get("kind") == "replace_full":
            code = edit.get("candidate_code", "") or ""
            py_ok = verify_python(code)
            if not py_ok.get("ok", False):
                return {
                    "applied": False,
                    "reason": f"post-apply static verify failed: {py_ok.get('reason', '')}",
                    "backups": backups,
                    "results": applied,
                    "verify": py_ok,
                }

    return {
        "applied": True,
        "reason": "plan applied and verified",
        "backups": backups,
        "results": applied,
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
            return base + repro_fix + regression + synthesized + prior + sandbox_bonus - blast_radius
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


def _normalize_candidates(candidates):
    if not isinstance(candidates, list):
        return candidates
    return [_normalize_candidate(c) for c in candidates]


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
    }


def _verify_candidate(candidate, context=None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""
    patch = c.get("patch", None)

    if kind in {"python_patch", "syntax"} and isinstance(code, str) and code.strip():
        return verify_python(code)

    if kind in {"dependency_install", "dependency"} or (
        isinstance(patch, str) and patch.strip().startswith("pip install ")
    ):
        return {"ok": True, "reason": "dependency install suggestion accepted as non-python command candidate", "mode": "dependency_install"}

    if kind == "runtime_file_missing":
        target_file = c.get("target_file") or getattr(context, "file_path", "")
        if target_file and str(target_file).endswith(".py"):
            if isinstance(code, str) and code.strip():
                py = verify_python(code)
                py["mode"] = kind
                py["reason"] = f"operational fix with python payload validation: {py.get('reason', '')}"
                return py
        return {"ok": True, "reason": "operational file fix for non-python target; skipped python syntax verification", "mode": kind}

    if kind in {"shell_command", "shell_runtime", "shell_command_missing", "shell_permission_denied", "shell_missing_path"}:
        return {"ok": True, "reason": "non-python operational fix; skipped python syntax verification", "mode": kind or "operational"}

    if isinstance(code, str) and code.strip():
        return verify_python(code)

    return {"ok": True, "reason": "no code payload"}


def _apply_candidate(candidate, file_path: str | None):
    c = _normalize_candidate(candidate)
    target_file = c.get("target_file") or file_path
    if not target_file:
        return {"applied": False, "reason": "no file_path provided", "backup_path": None}

    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"applied": False, "reason": f"candidate kind not auto-applicable: {kind or 'unknown'}", "backup_path": None}

    if not isinstance(code, str) or not code.strip():
        return {"applied": False, "reason": "candidate_code empty", "backup_path": None}

    backup = make_backup(target_file)
    apply_text_replacement(target_file, code)

    verify_result = verify_python(code)
    if not verify_result.get("ok", False):
        restore_backup(target_file, backup)
        return {
            "applied": False,
            "reason": "post-apply verification failed; restored backup",
            "backup_path": str(backup),
            "verify": verify_result,
        }

    return {
        "applied": True,
        "reason": "patch applied and verified",
        "backup_path": str(backup),
        "verify": verify_result,
        "target_file": target_file,
    }


def _execute_candidate(candidate, *, dry_run: bool = False, cwd: str | None = None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    metadata = c.get("metadata", {}) or {}
    patch = c.get("patch", None)

    if kind not in {"shell_command_missing", "shell_permission_denied", "shell_missing_path", "runtime_file_missing"}:
        return {"executed": False, "reason": f"candidate kind not executable: {kind or 'unknown'}", "results": []}

    command_text = patch
    if not command_text:
        suggestions = metadata.get("suggestions", [])
        if kind == "shell_command_missing":
            command_text = " && ".join(suggestions[:3]) if suggestions else None
        elif kind == "shell_permission_denied":
            command_text = " && ".join(suggestions[:2]) if suggestions else patch
        elif kind in {"shell_missing_path", "runtime_file_missing"}:
            command_text = " && ".join([s for s in suggestions if s.startswith(("mkdir -p", "touch", "chmod +x"))])

    return execute_safe_suggestions(command_text, dry_run=dry_run, cwd=cwd)


def _behavioral_verify_for_candidate(candidate, file_path: str | None, semantic_before: dict[str, Any] | None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    target_file = c.get("target_file") or file_path

    if not target_file or not str(target_file).endswith(".py"):
        return {"ok": True, "mode": "behavioral_skip", "reason": "non-python target; behavioral runtime verify skipped"}

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"ok": True, "mode": "behavioral_skip", "reason": f"candidate kind not behaviorally executed: {kind or 'unknown'}"}

    code = c.get("candidate_code", "") or ""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "mode": "behavioral_skip", "reason": "candidate_code empty"}

    before_stderr = (((semantic_before or {}).get("repro") or {}).get("stderr", "")) if isinstance(semantic_before, dict) else ""
    before_exception_type = (((semantic_before or {}).get("repro") or {}).get("exception_type", "")) if isinstance(semantic_before, dict) else ""

    backup = make_backup(target_file)
    try:
        apply_text_replacement(target_file, code)
        runtime = verify_python_runtime(target_file).to_dict()
        delta = verify_repro_delta(before_stderr, runtime.get("stderr", "")).to_dict()

        ok = bool(runtime.get("ok", False)) or bool(delta.get("ok", False))
        return {
            "ok": ok,
            "mode": "behavioral_verify",
            "reason": "behavioral verification completed",
            "runtime": runtime,
            "delta": delta,
            "before_exception_type": before_exception_type,
            "repro_fix_score": 0.75 if delta.get("ok", False) else 0.0,
            "regression_score": 0.65 if runtime.get("ok", False) else 0.0,
        }
    finally:
        restore_backup(target_file, backup)


def _synthesized_regression_tests(candidate, file_path: str | None, semantic_before: dict[str, Any] | None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    target_file = c.get("target_file") or file_path

    if not target_file or not str(target_file).endswith(".py"):
        return {"ok": True, "mode": "synth_skip", "reason": "non-python target; synthesized tests skipped", "score": 0.0}

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"ok": True, "mode": "synth_skip", "reason": f"candidate kind not synthesized-tested: {kind or 'unknown'}", "score": 0.0}

    code = c.get("candidate_code", "") or ""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "mode": "synth_skip", "reason": "candidate_code empty", "score": 0.0}

    before_stderr = (((semantic_before or {}).get("repro") or {}).get("stderr", "")) if isinstance(semantic_before, dict) else ""
    before_exception_type = (((semantic_before or {}).get("repro") or {}).get("exception_type", "")) if isinstance(semantic_before, dict) else ""

    replay = run_python_replay(file_path=target_file, candidate_code=code, target_file=target_file).to_dict()
    guard1_obj = check_failure_signature_removed(before_stderr, replay.get("stderr", ""))
    guard2_obj = check_expected_exception_absent(before_exception_type, replay.get("stderr", ""))
    combined = combine_regression_guards(guard1_obj, guard2_obj).to_dict()

    return {
        "ok": bool(combined.get("ok", False)),
        "mode": "synthesized_regression",
        "reason": "synthesized replay and regression guards evaluated",
        "score": float(combined.get("score", 0.0) or 0.0),
        "replay": replay,
        "guards": {
            "failure_signature_removed": guard1_obj.to_dict(),
            "exception_absent": guard2_obj.to_dict(),
            "combined": combined,
        },
    }


def _evaluate_candidates(candidates, *, file_path: str | None, semantic: dict[str, Any] | None):
    normalized = _normalize_candidates(candidates)
    enriched = []

    for cand in normalized:
        bv = _behavioral_verify_for_candidate(cand, file_path, semantic)
        cand2 = dict(cand)
        cand2["behavioral_verify"] = bv
        cand2["repro_fix_score"] = float(bv.get("repro_fix_score", 0.0) or 0.0)
        cand2["regression_score"] = float(bv.get("regression_score", 0.0) or 0.0)

        synth = _synthesized_regression_tests(cand2, file_path, semantic)
        cand2["synthesized_tests"] = synth
        cand2["synth_test_score"] = float(synth.get("score", 0.0) or 0.0)

        cand2["historical_success_prior"] = float(retrieval.candidate_history_prior(cand2) or 0.0)

        strategy = ((cand2.get("metadata") or {}).get("strategy", "")) if isinstance(cand2.get("metadata"), dict) else ""
        if strategy == "touch_only":
            cand2["blast_radius"] = 0.05
        elif strategy == "guard_exists":
            cand2["blast_radius"] = 0.12
        elif strategy == "try_except_recovery":
            cand2["blast_radius"] = 0.18
        else:
            cand2["blast_radius"] = float(cand2.get("blast_radius", 0.0) or 0.0)

        sandbox_context = build_context(error_text="", file_path=cand2.get("target_file") or file_path)
        cand2["sandbox"] = run_in_sandbox(cand2, sandbox_context)

        enriched.append(cand2)

    ranked = RankerAdapter().rank(enriched)
    best = ranked[0] if ranked else None
    return enriched, best


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False):
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    planner = _build_repair_planner_prelude(error_text=error_text, file_path=file_path, semantic=semantic)

    best_plan = (planner or {}).get("best_plan")
    plan_result = plan_to_candidate(best_plan) if best_plan else None
    verify_result = _verify_candidate(plan_result) if plan_result else {"ok": False, "reason": "no plan result"}
    behavioral_verify = plan_result.get("behavioral_verify") if isinstance(plan_result, dict) else None
    synthesized_tests = plan_result.get("synthesized_tests") if isinstance(plan_result, dict) else None
    sandbox_result = plan_result.get("sandbox") if isinstance(plan_result, dict) else None

    apply_result = apply_plan(best_plan) if auto_apply and best_plan else None
    exec_result = _execute_candidate(plan_result, dry_run=dry_run) if exec_suggestions and plan_result is not None else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "planner": planner,
        "result": plan_result,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
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
        "routes": ["planner_first"],
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
        "candidate_count": 1 if plan_result else 0,
        "candidates": [plan_result] if plan_result else [],
    }
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
    print("\\nDone.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
