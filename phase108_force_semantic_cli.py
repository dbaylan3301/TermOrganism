#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/cli/autofix_cli.py": r'''from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.autofix import run_autofix
from core.repro.harness import run_python_file


def _read_error_text_from_target(target: str) -> tuple[str, bool]:
    path = Path(target)
    if not path.exists():
        return f"Target not found: {target}", True

    if path.suffix == ".py":
        repro = run_python_file(str(path))
        if repro.reproduced:
            return repro.stderr or repro.stdout or "", True
        return "", False

    try:
        txt = path.read_text(encoding="utf-8")
    except Exception as exc:
        return str(exc), True

    return txt, bool(txt.strip())


def _print_human(result: dict):
    if result.get("ok") is True and result.get("message"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    best_plan = result.get("best_plan") or {}
    plan_result = result.get("result") or {}
    evidence = best_plan.get("evidence", {}) or {}

    print("TermOrganism Semantic Result")
    print("=" * 32)
    print("plan_id     :", best_plan.get("plan_id"))
    print("strategy    :", evidence.get("strategy"))
    print("score       :", best_plan.get("plan_score"))
    print("rank_tuple  :", best_plan.get("rank_tuple"))
    print("provider    :", evidence.get("provider"))
    print("caller      :", evidence.get("caller"))
    print("kind        :", ((best_plan.get("edits") or [{}])[0]).get("kind"))
    print("apply_ready :", bool(best_plan))
    print()

    if plan_result:
        print("normalized result:")
        print(json.dumps(plan_result, indent=2, ensure_ascii=False))
        print()

    planner = result.get("planner") or {}
    if planner:
        print("planner summary:")
        print(json.dumps({
            "candidate_count": planner.get("candidate_count"),
            "base_plan_count": planner.get("base_plan_count"),
            "multifile_plan_count": planner.get("multifile_plan_count"),
        }, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(prog="termorganism")
    parser.add_argument("target")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--auto-apply", action="store_true")
    parser.add_argument("--exec", dest="exec_suggestions", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--error-text", default=None)
    parser.add_argument("--force-semantic", action="store_true")
    args = parser.parse_args()

    target = args.target

    # explicit error text always wins
    if args.error_text:
        result = run_autofix(
            error_text=args.error_text,
            file_path=target,
            auto_apply=args.auto_apply,
            exec_suggestions=args.exec_suggestions,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            _print_human(result)
        return

    error_text, has_error = _read_error_text_from_target(target)

    # default healthy short-circuit unless force-semantic is enabled
    if (not has_error) and (not args.force_semantic):
        payload = {
            "ok": True,
            "message": "No error detected. Target appears healthy.",
            "target": target,
            "changed": False,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            _print_human(payload)
        return

    # force-semantic path: even if healthy, synthesize a semantic session
    if args.force_semantic and not error_text.strip():
        error_text = (
            f"FORCED_SEMANTIC_ANALYSIS\\n"
            f"Target: {target}\\n"
            f"Status: currently healthy or no direct runtime failure reproduced.\\n"
            f"Analyze semantic repair opportunities, cross-file contracts, and latent failure risks."
        )

    result = run_autofix(
        error_text=error_text,
        file_path=target,
        auto_apply=args.auto_apply,
        exec_suggestions=args.exec_suggestions,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_human(result)


if __name__ == "__main__":
    main()
''',

    "test_phase108_force_semantic_cli.py": r'''from __future__ import annotations

import json
import subprocess
import sys


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def main():
    baseline = run(["./termorganism", "demo/cross_file_dep.py", "--json"])
    forced = run(["./termorganism", "demo/cross_file_dep.py", "--json", "--force-semantic"])

    baseline_json = json.loads(baseline["stdout"])
    forced_json = json.loads(forced["stdout"])

    print(json.dumps({
        "baseline_ok": baseline_json.get("ok"),
        "baseline_message": baseline_json.get("message"),
        "forced_has_best_plan": bool(forced_json.get("best_plan")),
        "forced_best_plan_id": (forced_json.get("best_plan") or {}).get("plan_id"),
        "forced_strategy": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("strategy")),
        "forced_provider": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("provider")),
        "forced_caller": (((forced_json.get("best_plan") or {}).get("evidence") or {}).get("caller")),
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
