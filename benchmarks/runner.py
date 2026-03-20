from __future__ import annotations

import json
import os
import statistics
import subprocess
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "benchmarks" / "fixtures_manifest.json"
RESULTS_DIR = ROOT / "benchmarks" / "results"
REPORTS_DIR = ROOT / "benchmarks" / "reports"
TERMORGANISM_BIN = ROOT / "termorganism"


@dataclass
class CaseExpectation:
    result_present: bool | None = None
    best_plan_present: bool | None = None
    strategy_in: list[str] = field(default_factory=list)
    kind_in: list[str] = field(default_factory=list)
    provider_contains: list[str] = field(default_factory=list)
    caller_contains: list[str] = field(default_factory=list)
    target_file_contains: list[str] = field(default_factory=list)
    sandbox_ok: bool | None = None
    contract_ok: bool | None = None
    behavioral_ok: bool | None = None


@dataclass
class FixtureCase:
    id: str
    category: str
    target: str
    args: list[str]
    expected: CaseExpectation


@dataclass
class CaseResult:
    id: str
    category: str
    target: str
    command: list[str]
    returncode: int
    duration_ms: float
    stdout: str
    stderr: str
    parsed_ok: bool
    success: bool
    failure_reasons: list[str] = field(default_factory=list)
    extracted: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    success_rate: float
    median_fix_time_ms: float
    mean_fix_time_ms: float
    false_positive_rate: float
    category_stats: dict[str, Any]
    generated_files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest() -> list[FixtureCase]:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items: list[FixtureCase] = []
    for obj in raw:
        items.append(
            FixtureCase(
                id=obj["id"],
                category=obj["category"],
                target=obj["target"],
                args=list(obj.get("args", [])),
                expected=CaseExpectation(**obj.get("expected", {})),
            )
        )
    return items


def _strip_noise_prefix(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    cleaned: list[str] = []
    started = False
    for line in lines:
        stripped = line.lstrip()
        if not started:
            if stripped.startswith("{") or stripped.startswith("["):
                started = True
                cleaned.append(line)
            else:
                continue
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _json_load_loose(stdout: str) -> dict[str, Any] | None:
    text = (stdout or "").strip()
    if not text:
        return None

    candidates: list[str] = [text]

    stripped_prefix = _strip_noise_prefix(text)
    if stripped_prefix and stripped_prefix != text:
        candidates.append(stripped_prefix)

    if "```json" in text:
        frag = text.split("```json", 1)[1]
        frag = frag.split("```", 1)[0].strip()
        if frag:
            candidates.append(frag)

    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("{") and part.endswith("}"):
                candidates.append(part)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start:end + 1])

    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            loaded = json.loads(candidate)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            continue
    return None


def _extract_strategy(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    best_plan = payload.get("best_plan") or {}
    evidence = best_plan.get("evidence") or {}
    if evidence.get("strategy"):
        return str(evidence["strategy"]), "best_plan.evidence.strategy"

    result = payload.get("result") or {}
    metadata = result.get("metadata") or {}
    if metadata.get("strategy"):
        return str(metadata["strategy"]), "result.metadata.strategy"

    planner = payload.get("planner") or {}
    best_plan2 = planner.get("best_plan") or {}
    evidence2 = best_plan2.get("evidence") or {}
    if evidence2.get("strategy"):
        return str(evidence2["strategy"]), "planner.best_plan.evidence.strategy"

    return None, None


def _extract_kind(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    result = payload.get("result") or {}
    if result.get("kind"):
        return str(result["kind"]), "result.kind"

    best_plan = payload.get("best_plan") or {}
    edits = best_plan.get("edits") or []
    if edits and isinstance(edits[0], dict) and edits[0].get("kind"):
        return str(edits[0]["kind"]), "best_plan.edits[0].kind"

    return None, None


def _extract_provider(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    best_plan = payload.get("best_plan") or {}
    evidence = best_plan.get("evidence") or {}
    provider = evidence.get("provider")
    if provider:
        return str(provider), "best_plan.evidence.provider"

    planner = payload.get("planner") or {}
    best_plan2 = planner.get("best_plan") or {}
    evidence2 = best_plan2.get("evidence") or {}
    provider2 = evidence2.get("provider")
    if provider2:
        return str(provider2), "planner.best_plan.evidence.provider"

    return None, None


def _extract_caller(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    best_plan = payload.get("best_plan") or {}
    evidence = best_plan.get("evidence") or {}
    caller = evidence.get("caller")
    if caller:
        return str(caller), "best_plan.evidence.caller"

    planner = payload.get("planner") or {}
    best_plan2 = planner.get("best_plan") or {}
    evidence2 = best_plan2.get("evidence") or {}
    caller2 = evidence2.get("caller")
    if caller2:
        return str(caller2), "planner.best_plan.evidence.caller"

    return None, None


def _extract_target_file(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    result = payload.get("result") or {}
    if result.get("target_file"):
        return str(result["target_file"]), "result.target_file"
    if result.get("file_path_hint"):
        return str(result["file_path_hint"]), "result.file_path_hint"

    best_plan = payload.get("best_plan") or {}
    edits = best_plan.get("edits") or []
    if edits and isinstance(edits[0], dict) and edits[0].get("file"):
        return str(edits[0]["file"]), "best_plan.edits[0].file"

    return None, None


def _extract_bool(payload: dict[str, Any], key: str) -> tuple[bool | None, str | None]:
    value = payload.get(key)
    if isinstance(value, dict) and "ok" in value:
        return bool(value["ok"]), key
    return None, None


def _write_raw_capture(case: FixtureCase, stdout: str, stderr: str) -> dict[str, str]:
    stdout_path = RESULTS_DIR / f"{case.id}.stdout.txt"
    stderr_path = RESULTS_DIR / f"{case.id}.stderr.txt"
    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")
    return {
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def evaluate_case(case: FixtureCase) -> CaseResult:
    target_path = ROOT / case.target
    cmd = [str(TERMORGANISM_BIN), "repair", str(target_path.relative_to(ROOT))] + case.args

    clean_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(ROOT)),
        "TERM": os.environ.get("TERM", "xterm-256color"),
    }

    t0 = time.perf_counter()
    print(f"[CASE] {getattr(case, 'name', getattr(case, 'target', '<no-name>'))}", flush=True)
    print("[CMD] " + " ".join(map(str, cmd)), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=clean_env,
        timeout=60,
    )
    duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    payload = _json_load_loose(proc.stdout)
    parsed_ok = payload is not None
    failure_reasons: list[str] = []
    extracted: dict[str, Any] = {}

    if not parsed_ok:
        raw_paths = _write_raw_capture(case, proc.stdout, proc.stderr)
        failure_reasons.append("json_parse_failed")
        extracted.update(raw_paths)
        return CaseResult(
            id=case.id,
            category=case.category,
            target=case.target,
            command=cmd,
            returncode=proc.returncode,
            duration_ms=duration_ms,
            stdout=proc.stdout,
            stderr=proc.stderr,
            parsed_ok=False,
            success=False,
            failure_reasons=failure_reasons,
            extracted=extracted,
        )

    strategy, strategy_source = _extract_strategy(payload)
    kind, kind_source = _extract_kind(payload)
    provider, provider_source = _extract_provider(payload)
    caller, caller_source = _extract_caller(payload)
    target_file, target_file_source = _extract_target_file(payload)
    sandbox_ok, sandbox_source = _extract_bool(payload, "sandbox")
    contract_ok, contract_source = _extract_bool(payload, "contract_result")
    behavioral_ok, behavioral_source = _extract_bool(payload, "behavioral_verify")
    result_present = bool(payload.get("result"))
    best_plan_present = bool(payload.get("best_plan"))

    extracted = {
        "strategy": strategy,
        "strategy_source": strategy_source,
        "kind": kind,
        "kind_source": kind_source,
        "provider": provider,
        "provider_source": provider_source,
        "caller": caller,
        "caller_source": caller_source,
        "target_file": target_file,
        "target_file_source": target_file_source,
        "sandbox_ok": sandbox_ok,
        "sandbox_source": sandbox_source,
        "contract_ok": contract_ok,
        "contract_source": contract_source,
        "behavioral_ok": behavioral_ok,
        "behavioral_source": behavioral_source,
        "result_present": result_present,
        "best_plan_present": best_plan_present,
    }

    exp = case.expected

    if exp.result_present is not None and result_present != exp.result_present:
        failure_reasons.append(f"result_present_expected_{exp.result_present}")

    if exp.best_plan_present is not None and best_plan_present != exp.best_plan_present:
        failure_reasons.append(f"best_plan_present_expected_{exp.best_plan_present}")

    if exp.strategy_in and strategy not in exp.strategy_in:
        failure_reasons.append(f"strategy_not_in_expected:{strategy}")

    if exp.kind_in and kind not in exp.kind_in:
        failure_reasons.append(f"kind_not_in_expected:{kind}")

    if exp.provider_contains:
        joined = provider or ""
        if not any(token in joined for token in exp.provider_contains):
            failure_reasons.append(f"provider_mismatch:{provider}")

    if exp.caller_contains:
        joined = caller or ""
        if not any(token in joined for token in exp.caller_contains):
            failure_reasons.append(f"caller_mismatch:{caller}")

    if exp.target_file_contains:
        joined = target_file or ""
        if not any(token in joined for token in exp.target_file_contains):
            failure_reasons.append(f"target_file_mismatch:{target_file}")

    if exp.sandbox_ok is not None and sandbox_ok != exp.sandbox_ok:
        failure_reasons.append(f"sandbox_ok_expected_{exp.sandbox_ok}")

    if exp.contract_ok is not None and contract_ok != exp.contract_ok:
        failure_reasons.append(f"contract_ok_expected_{exp.contract_ok}")

    if exp.behavioral_ok is not None and behavioral_ok != exp.behavioral_ok:
        failure_reasons.append(f"behavioral_ok_expected_{exp.behavioral_ok}")

    return CaseResult(
        id=case.id,
        category=case.category,
        target=case.target,
        command=cmd,
        returncode=proc.returncode,
        duration_ms=duration_ms,
        stdout=proc.stdout,
        stderr=proc.stderr,
        parsed_ok=True,
        success=(len(failure_reasons) == 0),
        failure_reasons=failure_reasons,
        extracted=extracted,
    )


def category_breakdown(results: list[CaseResult]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    cats = sorted({r.category for r in results})
    for cat in cats:
        subset = [r for r in results if r.category == cat]
        passed = sum(1 for r in subset if r.success)
        total = len(subset)
        times = [r.duration_ms for r in subset]
        out[cat] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round((passed / total) if total else 0.0, 4),
            "median_fix_time_ms": round(statistics.median(times), 3) if times else 0.0,
            "mean_fix_time_ms": round(statistics.mean(times), 3) if times else 0.0,
        }
    return out


def false_positive_rate(results: list[CaseResult]) -> float:
    healthy_like = [
        r for r in results
        if "force-semantic" not in " ".join(r.command)
        and "cross_file_dep.py" in r.target
    ]
    if not healthy_like:
        return 0.0
    false_positive_count = sum(1 for r in healthy_like if r.extracted.get("result_present"))
    return round(false_positive_count / len(healthy_like), 4)


def write_case_results(results: list[CaseResult]) -> Path:
    path = RESULTS_DIR / "case_results.json"
    path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def write_summary(summary: BenchmarkSummary) -> Path:
    path = RESULTS_DIR / "benchmark_summary.json"
    path.write_text(
        json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def render_markdown_report(results: list[CaseResult], summary: BenchmarkSummary) -> str:
    lines: list[str] = []
    lines.append("# TermOrganism Benchmark Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total cases: {summary.total_cases}")
    lines.append(f"- Passed: {summary.passed_cases}")
    lines.append(f"- Failed: {summary.failed_cases}")
    lines.append(f"- Success rate: {summary.success_rate:.2%}")
    lines.append(f"- Median fix time: {summary.median_fix_time_ms:.3f} ms")
    lines.append(f"- Mean fix time: {summary.mean_fix_time_ms:.3f} ms")
    lines.append(f"- False positive rate: {summary.false_positive_rate:.2%}")
    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Total | Passed | Failed | Success Rate | Median Time (ms) | Mean Time (ms) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for category, data in summary.category_stats.items():
        lines.append(
            f"| {category} | {data['total']} | {data['passed']} | {data['failed']} | "
            f"{data['success_rate']:.2%} | {data['median_fix_time_ms']:.3f} | {data['mean_fix_time_ms']:.3f} |"
        )
    lines.append("")
    lines.append("## Case Results")
    lines.append("")
    lines.append("| Case ID | Category | Success | Strategy | Kind | Provider | Caller | Target File | Duration (ms) |")
    lines.append("|---|---|---|---|---|---|---|---:|")
    for r in results:
        e = r.extracted
        lines.append(
            f"| {r.id} | {r.category} | {'PASS' if r.success else 'FAIL'} | "
            f"{e.get('strategy') or ''} | {e.get('kind') or ''} | {e.get('provider') or ''} | "
            f"{e.get('caller') or ''} | {e.get('target_file') or ''} | {r.duration_ms:.3f} |"
        )

    failed = [r for r in results if not r.success]
    if failed:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for r in failed:
            lines.append(f"### {r.id}")
            lines.append("")
            for reason in r.failure_reasons:
                lines.append(f"- {reason}")
            if r.extracted.get("stdout_path"):
                lines.append(f"- stdout capture: `{r.extracted['stdout_path']}`")
            if r.extracted.get("stderr_path"):
                lines.append(f"- stderr capture: `{r.extracted['stderr_path']}`")
            lines.append("")

    return "\n".join(lines) + "\n"


def write_markdown_report(report: str) -> Path:
    path = REPORTS_DIR / "benchmark_report.md"
    path.write_text(report, encoding="utf-8")
    return path


def run_benchmark() -> BenchmarkSummary:
    ensure_dirs()
    fixtures = load_manifest()
    results = [evaluate_case(case) for case in fixtures]

    times = [r.duration_ms for r in results]
    passed_cases = sum(1 for r in results if r.success)
    total_cases = len(results)

    case_results_path = write_case_results(results)

    summary = BenchmarkSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        success_rate=round((passed_cases / total_cases) if total_cases else 0.0, 4),
        median_fix_time_ms=round(statistics.median(times), 3) if times else 0.0,
        mean_fix_time_ms=round(statistics.mean(times), 3) if times else 0.0,
        false_positive_rate=false_positive_rate(results),
        category_stats=category_breakdown(results),
        generated_files={
            "case_results_json": str(case_results_path),
        },
    )
    summary_path = write_summary(summary)
    report_path = write_markdown_report(render_markdown_report(results, summary))
    summary.generated_files["summary_json"] = str(summary_path)
    summary.generated_files["report_md"] = str(report_path)
    write_summary(summary)
    return summary


if __name__ == "__main__":
    summary = run_benchmark()
    print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
