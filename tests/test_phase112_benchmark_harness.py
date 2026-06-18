from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "benchmarks/runner.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(proc.returncode)

    payload = json.loads(proc.stdout)

    report_path = ROOT / "benchmarks" / "reports" / "benchmark_report.md"
    summary_path = ROOT / "benchmarks" / "results" / "benchmark_summary.json"
    cases_path = ROOT / "benchmarks" / "results" / "case_results.json"

    out = {
        "total_cases": payload["total_cases"],
        "passed_cases": payload["passed_cases"],
        "failed_cases": payload["failed_cases"],
        "success_rate": payload["success_rate"],
        "median_fix_time_ms": payload["median_fix_time_ms"],
        "mean_fix_time_ms": payload["mean_fix_time_ms"],
        "false_positive_rate": payload["false_positive_rate"],
        "report_exists": report_path.exists(),
        "summary_exists": summary_path.exists(),
        "case_results_exists": cases_path.exists(),
        "categories": sorted(payload["category_stats"].keys()),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
