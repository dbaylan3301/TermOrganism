from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Any

REPO = Path("/root/TermOrganismGitFork")
TMP = Path("/tmp/termorganism_bench")
TMP.mkdir(parents=True, exist_ok=True)

CASES = {
    "missing_import": '''import definitely_missing_package_3301\nprint("x")\n''',
    "missing_path": '''with open("totally_missing_file_3301.txt") as f:\n    print(f.read())\n''',
    "eval_and_path": '''x = eval("1+1")\nwith open("totally_missing_file_3301.txt") as f:\n    print(f.read())\n''',
    "bare_except": '''def f():\n    try:\n        return 1\n    except:\n        return 0\n''',
    "mutable_default": '''def collect(a=[]):\n    a.append(1)\n    return a\n''',
    "cli_main_guard": '''import argparse\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.parse_args()\n    return 0\n''',
}


def run_case(name: str, content: str) -> dict[str, Any]:
    path = TMP / f"{name}.py"
    path.write_text(content, encoding="utf-8")

    env = dict(__import__("os").environ)
    env["TERMORGANISM_USE_DAEMON"] = "0"
    p = subprocess.run(
        ["./termorganism", "repair", str(path), "--json"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        env=env,
    )
    if p.returncode != 0:
        return {"case": name, "error": p.stderr or p.stdout}

    data = json.loads(p.stdout)
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]

    if data.get("success") is False and data.get("error"):
        return {
            "case": name,
            "error": data.get("error"),
        }

    routing = data.get("routing") or {}
    return {
        "case": name,
        "signature": data.get("signature"),
        "planner": routing.get("planner_suggested_mode"),
        "final": routing.get("effective_mode"),
        "planner_reason": routing.get("planner_reason"),
        "intent_reason": routing.get("intent_reason"),
        "bridge_score": routing.get("bridge_score"),
        "bridge_route": routing.get("bridge_recommended_route"),
        "whisper_kind": routing.get("whisper_kind"),
        "whisper_priority": routing.get("whisper_priority"),
        "arbitration_winner": routing.get("arbitration_winner"),
        "arbitration_count": routing.get("arbitration_candidate_count"),
        "arbitration_reason": routing.get("arbitration_reason"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if not r.get("error")]
    changed = [r for r in ok if r.get("planner") != r.get("final")]
    whisper = [r for r in ok if r.get("whisper_kind")]
    bridge = [r for r in ok if (r.get("bridge_score") or 0) > 0]
    return {
        "total_cases": len(rows),
        "successful_cases": len(ok),
        "planner_changed_count": len(changed),
        "whisper_cases": len(whisper),
        "bridge_scored_cases": len(bridge),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-benchmark-proactive")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", dest="csv_path", default="")
    args = parser.parse_args()

    rows = [run_case(name, content) for name, content in CASES.items()]
    summary = summarize(rows)

    if args.csv_path:
        fieldnames = sorted({k for row in rows for k in row.keys()})
        with open(args.csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow(row)

    if args.json:
        print(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2))
        return 0

    print("TermOrganism Proactive Benchmark")
    print("--------------------------------")
    print(f"total_cases: {summary['total_cases']}")
    print(f"successful_cases: {summary['successful_cases']}")
    print(f"planner_changed_count: {summary['planner_changed_count']}")
    print(f"whisper_cases: {summary['whisper_cases']}")
    print(f"bridge_scored_cases: {summary['bridge_scored_cases']}")
    print()

    for row in rows:
        if row.get("error"):
            print(f"- {row['case']}: ERROR")
            print(f"  {row['error']}")
            print()
            continue

        print(f"- {row['case']}")
        print(f"  signature: {row['signature']}")
        print(f"  planner:   {row['planner']}")
        print(f"  final:     {row['final']}")
        print(f"  bridge:    {row['bridge_route']} ({row['bridge_score']})")
        print(f"  whisper:   {row['whisper_kind']} ({row['whisper_priority']})")
        print(f"  winner:    {row['arbitration_winner']} / {row['arbitration_count']}")
        print(f"  reason:    {row['planner_reason']}")
        if row.get("intent_reason"):
            print(f"  intent:    {row['intent_reason']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
