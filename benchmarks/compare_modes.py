from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "benchmarks" / "results"
REPORTS_DIR = REPO_ROOT / "benchmarks" / "reports"

SUMMARY_PATH = RESULTS_DIR / "benchmark_summary.json"
CASES_PATH = RESULTS_DIR / "case_results.json"

NORMAL_SUMMARY_COPY = RESULTS_DIR / "benchmark_summary.normal.json"
FAST_SUMMARY_COPY = RESULTS_DIR / "benchmark_summary.fast.json"
NORMAL_CASES_COPY = RESULTS_DIR / "case_results.normal.json"
FAST_CASES_COPY = RESULTS_DIR / "case_results.fast.json"

COMPARE_REPORT = REPORTS_DIR / "benchmark_compare.md"

NORMAL_STDOUT = RESULTS_DIR / "benchmark_normal.stdout.txt"
NORMAL_STDERR = RESULTS_DIR / "benchmark_normal.stderr.txt"
FAST_STDOUT = RESULTS_DIR / "benchmark_fast.stdout.txt"
FAST_STDERR = RESULTS_DIR / "benchmark_fast.stderr.txt"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_number(d: dict[str, Any] | None, *keys: str) -> float | None:
    if not isinstance(d, dict):
        return None
    for key in keys:
        val = d.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copy2(src, dst)


def _run_mode(name: str, fast: bool) -> dict[str, Any]:
    env = os.environ.copy()
    if fast:
        env["TERMORGANISM_FAST"] = "1"
    else:
        env.pop("TERMORGANISM_FAST", None)

    cmd = [sys.executable, "-u", "benchmarks/runner.py"]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    stdout_path = FAST_STDOUT if fast else NORMAL_STDOUT
    stderr_path = FAST_STDERR if fast else NORMAL_STDERR
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    enrich_cmd = [sys.executable, "-u", "benchmarks/enrich_case_results.py"]
    enrich_proc = subprocess.run(
        enrich_cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    summary = _load_json(SUMMARY_PATH)
    cases = _load_json(CASES_PATH)

    if fast:
        _copy_if_exists(SUMMARY_PATH, FAST_SUMMARY_COPY)
        _copy_if_exists(CASES_PATH, FAST_CASES_COPY)
    else:
        _copy_if_exists(SUMMARY_PATH, NORMAL_SUMMARY_COPY)
        _copy_if_exists(CASES_PATH, NORMAL_CASES_COPY)

    return {
        "name": name,
        "fast": fast,
        "returncode": proc.returncode,
        "summary": summary,
        "cases": cases,
        "stdout_file": str(stdout_path),
        "stderr_file": str(stderr_path),
        "enrich_returncode": enrich_proc.returncode,
        "enrich_stdout": enrich_proc.stdout,
        "enrich_stderr": enrich_proc.stderr,
    }


def _count_cases(cases: Any) -> int:
    return len(_extract_case_list(cases))


def _walk_confidence_scores(obj: Any, out: list[float]) -> None:
    if isinstance(obj, dict):
        conf = obj.get("confidence")
        if isinstance(conf, dict):
            score = conf.get("score")
            if isinstance(score, (int, float)):
                out.append(float(score))
        for v in obj.values():
            _walk_confidence_scores(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_confidence_scores(item, out)


def _avg_confidence(cases: Any) -> float | None:
    scores: list[float] = []
    _walk_confidence_scores(cases, scores)
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def _extract_case_list(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]

    if isinstance(obj, dict):
        for key in ("cases", "results", "items"):
            v = obj.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]

        # fallback: maybe dict-of-case-name -> payload
        if obj and all(isinstance(v, dict) for v in obj.values()):
            out = []
            for k, v in obj.items():
                if isinstance(v, dict):
                    item = dict(v)
                    item.setdefault("case_name", str(k))
                    out.append(item)
            return out

    return []


def _first_present(d: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in d:
            return d.get(key)
    return None


def _extract_case_name(case: dict[str, Any], index: int) -> str:
    name = _first_present(
        case,
        "case_name",
        "name",
        "id",
        "case_id",
        "slug",
        "title",
        "target",
        "target_file",
        "file_path",
    )
    if name is not None:
        return str(name)
    return f"case_{index+1}"


def _infer_category_from_name(name: str) -> str:
    s = name.lower()
    if "cross" in s or "multifile" in s or "semantic" in s:
        return "cross-file"
    if "shell" in s or "command" in s:
        return "shell"
    if "dependency" in s or "import" in s or "module" in s:
        return "dependency"
    if "runtime" in s or "file" in s or "config" in s or "env" in s:
        return "runtime"
    return "other"


def _extract_category(case: dict[str, Any], name: str) -> str:
    category = _first_present(case, "category", "group", "suite", "kind")
    if category:
        return str(category)
    return _infer_category_from_name(name)


def _extract_success(case: dict[str, Any]) -> bool | None:
    for key in ("ok", "passed", "success"):
        val = case.get(key)
        if isinstance(val, bool):
            return val
    status = case.get("status")
    if isinstance(status, str):
        s = status.lower()
        if s in {"ok", "passed", "success"}:
            return True
        if s in {"fail", "failed", "error"}:
            return False
    return None


def _extract_latency(case: dict[str, Any]) -> float | None:
    # direct fields
    direct = _extract_number(
        case,
        "elapsed_ms",
        "latency_ms",
        "time_ms",
        "duration_ms",
        "fix_time_ms",
        "runtime_ms",
    )
    if direct is not None:
        return direct

    # nested metrics
    metrics = case.get("metrics")
    if isinstance(metrics, dict):
        nested = _extract_number(
            metrics,
            "total_ms",
            "elapsed_ms",
            "latency_ms",
            "time_ms",
            "duration_ms",
            "fix_time_ms",
        )
        if nested is not None:
            return nested

    # fallback summary-like nested blocks
    for key in ("result", "payload", "repair", "verification"):
        blk = case.get(key)
        if isinstance(blk, dict):
            nested = _extract_number(
                blk,
                "elapsed_ms",
                "latency_ms",
                "time_ms",
                "duration_ms",
                "fix_time_ms",
            )
            if nested is not None:
                return nested
            metrics = blk.get("metrics")
            if isinstance(metrics, dict):
                nested = _extract_number(
                    metrics,
                    "total_ms",
                    "elapsed_ms",
                    "latency_ms",
                    "time_ms",
                    "duration_ms",
                    "fix_time_ms",
                )
                if nested is not None:
                    return nested

    return None


def _extract_case_confidence(case: dict[str, Any]) -> float | None:
    found: list[float] = []
    _walk_confidence_scores(case, found)
    if found:
        return round(max(found), 3)
    return None


def _build_case_index(cases: Any) -> dict[str, dict[str, Any]]:
    rows = {}
    case_list = _extract_case_list(cases)
    for i, case in enumerate(case_list):
        name = _extract_case_name(case, i)
        rows[name] = {
            "name": name,
            "category": _extract_category(case, name),
            "ok": _extract_success(case),
            "latency_ms": _extract_latency(case),
            "confidence": _extract_case_confidence(case),
            "raw": case,
        }
    return rows


def _median(vals: list[float]) -> float | None:
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return round(statistics.median(vals), 3)


def _mean(vals: list[float]) -> float | None:
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def _metric_bundle(run: dict[str, Any]) -> dict[str, Any]:
    summary = run.get("summary") or {}
    cases = run.get("cases")
    return {
        "success_rate": _extract_number(summary, "success_rate"),
        "median_ms": _extract_number(summary, "median_fix_time_ms", "median_time_ms", "median_ms"),
        "mean_ms": _extract_number(summary, "mean_fix_time_ms", "mean_time_ms", "mean_ms", "avg_ms"),
        "passed": _extract_number(summary, "passed", "passed_count"),
        "total": _extract_number(summary, "total", "total_count", "case_count"),
        "timeout_count": _extract_number(summary, "timeout_count"),
        "avg_confidence": _avg_confidence(cases),
        "case_count": _count_cases(cases),
    }


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _category_breakdown(normal_cases: Any, fast_cases: Any) -> list[dict[str, Any]]:
    n_idx = _build_case_index(normal_cases)
    f_idx = _build_case_index(fast_cases)
    names = sorted(set(n_idx) | set(f_idx))

    by_cat: dict[str, dict[str, list[float]]] = {}
    for name in names:
        n = n_idx.get(name, {})
        f = f_idx.get(name, {})
        cat = n.get("category") or f.get("category") or "other"
        by_cat.setdefault(cat, {
            "normal_latencies": [],
            "fast_latencies": [],
            "normal_conf": [],
            "fast_conf": [],
            "normal_ok": [],
            "fast_ok": [],
        })
        if isinstance(n.get("latency_ms"), (int, float)):
            by_cat[cat]["normal_latencies"].append(float(n["latency_ms"]))
        if isinstance(f.get("latency_ms"), (int, float)):
            by_cat[cat]["fast_latencies"].append(float(f["latency_ms"]))
        if isinstance(n.get("confidence"), (int, float)):
            by_cat[cat]["normal_conf"].append(float(n["confidence"]))
        if isinstance(f.get("confidence"), (int, float)):
            by_cat[cat]["fast_conf"].append(float(f["confidence"]))
        if isinstance(n.get("ok"), bool):
            by_cat[cat]["normal_ok"].append(1.0 if n["ok"] else 0.0)
        if isinstance(f.get("ok"), bool):
            by_cat[cat]["fast_ok"].append(1.0 if f["ok"] else 0.0)

    rows = []
    for cat, vals in sorted(by_cat.items()):
        rows.append({
            "category": cat,
            "normal_median_ms": _median(vals["normal_latencies"]),
            "fast_median_ms": _median(vals["fast_latencies"]),
            "normal_mean_ms": _mean(vals["normal_latencies"]),
            "fast_mean_ms": _mean(vals["fast_latencies"]),
            "normal_avg_conf": _mean(vals["normal_conf"]),
            "fast_avg_conf": _mean(vals["fast_conf"]),
            "normal_success": _mean(vals["normal_ok"]),
            "fast_success": _mean(vals["fast_ok"]),
            "count": max(len(vals["normal_latencies"]), len(vals["fast_latencies"])),
        })
    return rows


def _case_deltas(normal_cases: Any, fast_cases: Any) -> list[dict[str, Any]]:
    n_idx = _build_case_index(normal_cases)
    f_idx = _build_case_index(fast_cases)
    names = sorted(set(n_idx) | set(f_idx))

    rows = []
    for name in names:
        n = n_idx.get(name, {})
        f = f_idx.get(name, {})
        n_ms = n.get("latency_ms")
        f_ms = f.get("latency_ms")
        delta = None
        if isinstance(n_ms, (int, float)) and isinstance(f_ms, (int, float)):
            delta = round(float(f_ms) - float(n_ms), 3)

        rows.append({
            "name": name,
            "category": n.get("category") or f.get("category") or "other",
            "normal_ok": n.get("ok"),
            "fast_ok": f.get("ok"),
            "normal_ms": n_ms,
            "fast_ms": f_ms,
            "delta_ms": delta,
            "normal_conf": n.get("confidence"),
            "fast_conf": f.get("confidence"),
        })
    return rows


def _write_compare_report(normal: dict[str, Any], fast: dict[str, Any]) -> None:
    n = _metric_bundle(normal)
    f = _metric_bundle(fast)
    category_rows = _category_breakdown(normal.get("cases"), fast.get("cases"))
    case_rows = _case_deltas(normal.get("cases"), fast.get("cases"))

    faster = [r for r in case_rows if isinstance(r.get("delta_ms"), (int, float)) and r["delta_ms"] < 0]
    slower = [r for r in case_rows if isinstance(r.get("delta_ms"), (int, float)) and r["delta_ms"] > 0]

    faster = sorted(faster, key=lambda r: r["delta_ms"])[:5]
    slower = sorted(slower, key=lambda r: r["delta_ms"], reverse=True)[:5]

    lines = []
    lines.append("# Benchmark mode comparison")
    lines.append("")
    lines.append("| Mode | Return Code | Cases | Timeout Count | Success Rate | Median ms | Mean ms | Avg Confidence |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| normal | {_fmt(normal.get('returncode'))} | {_fmt(n['case_count'])} | {_fmt(n['timeout_count'])} | {_fmt(n['success_rate'])} | {_fmt(n['median_ms'])} | {_fmt(n['mean_ms'])} | {_fmt(n['avg_confidence'])} |"
    )
    lines.append(
        f"| fast | {_fmt(fast.get('returncode'))} | {_fmt(f['case_count'])} | {_fmt(f['timeout_count'])} | {_fmt(f['success_rate'])} | {_fmt(f['median_ms'])} | {_fmt(f['mean_ms'])} | {_fmt(f['avg_confidence'])} |"
    )

    lines.append("")
    lines.append("## Category breakdown")
    lines.append("")
    lines.append("| Category | Count | Normal Success | Fast Success | Normal Median ms | Fast Median ms | Normal Mean ms | Fast Mean ms | Normal Avg Confidence | Fast Avg Confidence |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in category_rows:
        lines.append(
            f"| {row['category']} | {_fmt(row['count'])} | {_fmt(row['normal_success'])} | {_fmt(row['fast_success'])} | {_fmt(row['normal_median_ms'])} | {_fmt(row['fast_median_ms'])} | {_fmt(row['normal_mean_ms'])} | {_fmt(row['fast_mean_ms'])} | {_fmt(row['normal_avg_conf'])} | {_fmt(row['fast_avg_conf'])} |"
        )

    lines.append("")
    lines.append("## Fastest improvements")
    lines.append("")
    lines.append("| Case | Category | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    if faster:
        for row in faster:
            lines.append(
                f"| {row['name']} | {row['category']} | {_fmt(row['normal_ms'])} | {_fmt(row['fast_ms'])} | {_fmt(row['delta_ms'])} | {_fmt(row['normal_conf'])} | {_fmt(row['fast_conf'])} |"
            )
    else:
        lines.append("| - | - | - | - | - | - | - |")

    lines.append("")
    lines.append("## Largest regressions")
    lines.append("")
    lines.append("| Case | Category | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    if slower:
        for row in slower:
            lines.append(
                f"| {row['name']} | {row['category']} | {_fmt(row['normal_ms'])} | {_fmt(row['fast_ms'])} | {_fmt(row['delta_ms'])} | {_fmt(row['normal_conf'])} | {_fmt(row['fast_conf'])} |"
            )
    else:
        lines.append("| - | - | - | - | - | - | - |")

    lines.append("")
    lines.append("## Case-by-case")
    lines.append("")
    lines.append("| Case | Category | Normal OK | Fast OK | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in case_rows:
        lines.append(
            f"| {row['name']} | {row['category']} | {_fmt(row['normal_ok'])} | {_fmt(row['fast_ok'])} | {_fmt(row['normal_ms'])} | {_fmt(row['fast_ms'])} | {_fmt(row['delta_ms'])} | {_fmt(row['normal_conf'])} | {_fmt(row['fast_conf'])} |"
        )

    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append(f"- normal summary: `{NORMAL_SUMMARY_COPY}`")
    lines.append(f"- fast summary: `{FAST_SUMMARY_COPY}`")
    lines.append(f"- normal cases: `{NORMAL_CASES_COPY}`")
    lines.append(f"- fast cases: `{FAST_CASES_COPY}`")
    lines.append(f"- normal stdout: `{NORMAL_STDOUT}`")
    lines.append(f"- fast stdout: `{FAST_STDOUT}`")
    lines.append(f"- normal stderr: `{NORMAL_STDERR}`")
    lines.append(f"- fast stderr: `{FAST_STDERR}`")

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `TERMORGANISM_FAST=1` was used for fast mode.")
    lines.append("- Confidence is collected by recursively scanning each case payload for `confidence.score`.")
    lines.append("- Existing `benchmarks/runner.py` remains untouched; this compare wrapper is additive.")

    COMPARE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[compare] running normal benchmark...")
    normal = _run_mode("normal", fast=False)

    print("[compare] running fast benchmark...")
    fast = _run_mode("fast", fast=True)

    _write_compare_report(normal, fast)

    print("[compare] wrote:", COMPARE_REPORT)
    print("[compare] normal rc:", normal["returncode"])
    print("[compare] fast rc:", fast["returncode"])

    return 0 if normal["returncode"] == 0 and fast["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
