#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/planner/repair_planner.py": r'''from __future__ import annotations

from typing import Any


def _normalize_strategy(candidate: dict[str, Any]) -> str:
    metadata = dict(candidate.get("metadata", {}) or {})
    strategy = str(metadata.get("strategy", "") or "").strip()
    if strategy:
        return strategy

    code = str(candidate.get("candidate_code", "") or "")
    summary = str(candidate.get("summary", "") or "")
    hypothesis = str(candidate.get("hypothesis", "") or "")
    blob = " ".join([code, summary, hypothesis])

    if 'exists() else ""' in code or "exists() fallback" in blob:
        return "guard_exists"
    if "except FileNotFoundError" in code or "FileNotFoundError recovery" in blob:
        return "try_except_recovery"
    if (candidate.get("patch") and not code.strip()) or "create missing runtime path" in blob:
        return "touch_only"
    return "unknown"


def _candidate_to_plan(candidate: dict[str, Any], file_path: str | None) -> dict[str, Any]:
    metadata = dict(candidate.get("metadata", {}) or {})
    strategy = _normalize_strategy(candidate)

    target_file = (
        candidate.get("target_file")
        or candidate.get("file_path_hint")
        or file_path
    )

    patch = candidate.get("patch")
    candidate_code = str(candidate.get("candidate_code", "") or "")
    summary = str(candidate.get("summary", "") or "")
    hypothesis = str(candidate.get("hypothesis", "") or "")
    semantic_claim = str(candidate.get("semantic_claim", "") or "")

    if strategy == "touch_only":
        edit = {
            "file": target_file,
            "kind": "operational",
            "summary": summary or "operational fix",
            "commands": metadata.get("shell_steps", []) or ([patch] if patch else []),
            "candidate_code": "",
        }
    else:
        edit = {
            "file": target_file,
            "kind": "replace_full",
            "summary": summary or "code repair",
            "candidate_code": candidate_code,
        }

    expected_behavior = {
        "exception_absent": "FileNotFoundError",
        "exit_code": 0,
    }

    return {
        "plan_id": f"plan_{strategy}_{abs(hash((target_file, summary, strategy, candidate_code))) % 100000}",
        "hypothesis": hypothesis,
        "semantic_claim": semantic_claim,
        "root_cause_nodes": [],
        "target_files": [target_file] if target_file else [],
        "edits": [edit],
        "expected_behavior": expected_behavior,
        "evidence": {
            "strategy": strategy,
            "localization_target": target_file,
            "source_candidate_summary": summary,
        },
        "confidence": float(candidate.get("confidence", 0.0) or 0.0),
        "risk": float(candidate.get("blast_radius", 0.0) or 0.0),
        "blast_radius": float(candidate.get("blast_radius", 0.0) or 0.0),
    }


def build_repair_plans(
    *,
    error_text: str,
    semantic: dict[str, Any] | None,
    causes: list[dict[str, Any]] | None,
    project_graph: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None = None,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []

    for cand in candidates or []:
        if not isinstance(cand, dict):
            continue
        plans.append(_candidate_to_plan(cand, file_path=file_path))

    if plans:
        return plans

    target = file_path
    return [{
        "plan_id": "plan_runtime_operational_fallback",
        "hypothesis": "missing path may be sufficient; create runtime file path without source edits",
        "root_cause_nodes": [],
        "target_files": [target] if target else [],
        "edits": [{
            "file": target,
            "kind": "operational",
            "summary": "create missing runtime path",
            "commands": ["mkdir -p logs", "touch logs/app.log"],
            "candidate_code": "",
        }],
        "expected_behavior": {
            "exception_absent": "FileNotFoundError",
            "exit_code": 0,
        },
        "evidence": {
            "strategy": "touch_only",
            "localization_target": target,
        },
        "confidence": 0.66,
        "risk": 0.08,
        "blast_radius": 0.05,
    }]
''',

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
    return 0.10


def _infer_strategy(plan: dict[str, Any]) -> str:
    evidence = plan.get("evidence", {}) or {}
    strategy = str(evidence.get("strategy", "") or "").strip()
    if strategy and strategy != "unknown":
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

    return "unknown"


def _has_code_edit(plan: dict[str, Any]) -> bool:
    for edit in plan.get("edits", []) or []:
        if edit.get("kind") == "replace_full" and str(edit.get("candidate_code", "") or "").strip():
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
    code_bonus = 0.55 if has_code else -0.45

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

    return (
        has_code,
        contract_score,
        propagation_score,
        semantic_priority,
        round(final_score, 6),
    )


def annotate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    rt = _rank_tuple(plan)
    out = dict(plan)
    out["rank_tuple"] = list(rt)
    out["plan_score"] = float(rt[-1])
    return out


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = [annotate_plan(dict(p)) for p in (plans or [])]
    annotated.sort(key=lambda p: tuple(p.get("rank_tuple", [])), reverse=True)
    return annotated
''',

    "test_phase106_edit_payload.py": r'''from __future__ import annotations

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
best_edit = ((best.get("edits") or [{}])[0])

print(json.dumps({
    "best_plan_id": best.get("plan_id"),
    "strategy": (best.get("evidence") or {}).get("strategy"),
    "rank_tuple": best.get("rank_tuple"),
    "best_edit_kind": best_edit.get("kind"),
    "best_has_candidate_code": bool((best_edit.get("candidate_code", "") or "").strip()),
    "top_8": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "kind": ((p.get("edits") or [{}])[0]).get("kind"),
            "has_candidate_code": bool((((p.get("edits") or [{}])[0]).get("candidate_code", "") or "").strip()),
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
