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

    # Cross-file edits deserve a bit more caution than single-file edits
    new_plan["risk"] = max(float(best_plan.get("risk", 0.12) or 0.12), 0.14)
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
    evidence = plan.get("evidence", {}) or {}

    branch_bonus = 0.80 if branch.get("ok") else 0.0
    contract_bonus = float(contract.get("score", 0.0) or 0.0)
    propagation_bonus = float(propagation.get("score", 0.0) or 0.0)

    edit_count = len(plan.get("edits", []) or [])
    complexity_penalty = max(0, edit_count - 1) * 0.05

    multifile_bonus = 0.10 if evidence.get("multifile") is True else 0.0

    strategy = str(evidence.get("strategy", "") or "")
    semantic_bonus = 0.0
    semantic_penalty = 0.0

    if strategy == "guard_exists":
        semantic_bonus += 0.45
    elif strategy == "try_except_recovery":
        semantic_bonus += 0.25
    elif strategy == "touch_only":
        semantic_penalty += 0.35

    return (
        confidence
        + branch_bonus
        + contract_bonus
        + propagation_bonus
        + multifile_bonus
        + semantic_bonus
        - semantic_penalty
        - risk
        - blast_radius
        - complexity_penalty
    )


def rank_plans(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(plans, key=score_plan, reverse=True)
''',

    "test_phase101_cross_file.py": r'''from __future__ import annotations

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
    "same_target_bug": ev.get("provider") == ev.get("caller"),
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
