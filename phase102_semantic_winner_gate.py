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


def _has_code_edit(plan: dict[str, Any]) -> bool:
    for edit in plan.get("edits", []) or []:
        if edit.get("kind") == "replace_full" and (edit.get("candidate_code", "") or "").strip():
            return True
    return False


def score_plan(plan: dict[str, Any]) -> float:
    confidence = float(plan.get("confidence", 0.0) or 0.0)
    risk = float(plan.get("risk", 0.0) or 0.0)
    blast_radius = float(plan.get("blast_radius", 0.0) or 0.0)

    branch = plan.get("branch_result", {}) or {}
    contract = plan.get("contract_result", {}) or {}
    propagation = plan.get("contract_propagation", {}) or {}
    evidence = plan.get("evidence", {}) or {}

    strategy = str(evidence.get("strategy", "") or "")
    multifile = evidence.get("multifile") is True

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_bonus = float(contract.get("score", 0.0) or 0.0)
    propagation_bonus = float(propagation.get("score", 0.0) or 0.0)

    semantic_weight = _strategy_semantic_weight(strategy)
    semantic_bonus = semantic_weight * 0.90

    multifile_bonus = 0.20 if multifile else 0.0
    code_edit_bonus = 0.35 if _has_code_edit(plan) else -0.45

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    return (
        confidence
        + branch_bonus
        + contract_bonus
        + propagation_bonus
        + semantic_bonus
        + multifile_bonus
        + code_edit_bonus
        - risk
        - blast_radius
        - complexity_penalty
    )


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(plans, key=score_plan, reverse=True)

    def sort_key(plan: dict[str, Any]):
        evidence = plan.get("evidence", {}) or {}
        strategy = str(evidence.get("strategy", "") or "")
        has_code = _has_code_edit(plan)
        contract_score = float(((plan.get("contract_result") or {}).get("score", 0.0)) or 0.0)
        propagation_score = float(((plan.get("contract_propagation") or {}).get("score", 0.0)) or 0.0)

        semantic_priority = {
            "guard_exists": 3,
            "try_except_recovery": 2,
            "touch_only": 1,
        }.get(strategy, 0)

        return (
            has_code,
            contract_score,
            propagation_score,
            semantic_priority,
            score_plan(plan),
        )

    ranked = sorted(ranked, key=sort_key, reverse=True)
    return ranked
''',

    "test_phase102_winner_gate.py": r'''from __future__ import annotations

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

best = res.get("best_plan") or {}
ev = best.get("evidence") or {}

print(json.dumps({
    "best_plan_id": best.get("plan_id"),
    "strategy": ev.get("strategy"),
    "provider": ev.get("provider"),
    "caller": ev.get("caller"),
    "target_files": best.get("target_files"),
    "has_code_edit": any(
        (e.get("kind") == "replace_full" and (e.get("candidate_code", "") or "").strip())
        for e in (best.get("edits") or [])
    ),
    "plan_score": res.get("plan_score"),
    "contract_propagation": res.get("contract_propagation"),
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
