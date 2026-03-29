from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "benchmarks" / "results" / "benchmark_summary.json"


def read_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def render_readme_snippet() -> str:
    s = read_summary()
    return (
        "## Benchmark Snapshot\n\n"
        f"- Total cases: {s['total_cases']}\n"
        f"- Success rate: {s['success_rate']:.2%}\n"
        f"- Median fix time: {s['median_fix_time_ms']:.3f} ms\n"
        f"- False positive rate: {s['false_positive_rate']:.2%}\n"
    )


if __name__ == "__main__":
    print(render_readme_snippet())
