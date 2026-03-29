#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import textwrap

ROOT = Path.cwd()

PATCHES: dict[str, str] = {
    "benchmarks/__init__.py": "",
    "benchmarks/cases/README.md": textwrap.dedent("""\
        # Benchmark Cases

        Each case directory should contain:

        - `input_target.txt` or a direct target path in manifest
        - `expected.json`
        - optional `notes.txt`

        `expected.json` schema:

        ```json
        {
          "id": "runtime_missing_file_basic",
          "category": "runtime",
          "target": "demo/broken_runtime.py",
          "expect": {
            "result_present": true,
            "strategy_in": ["guard_exists", "try_except_recovery", "touch_only"],
            "target_file_contains": ["broken_runtime.py", "helper_mod.py"],
            "provider_contains": ["helper_mod.py"],
            "caller_contains": ["cross_file_dep.py"],
            "sandbox_ok": true,
            "contract_ok": true,
            "behavioral_ok": true
          }
        }
        ```
    """),
    "benchmarks/fixtures_manifest.json": textwrap.dedent("""\
        [
          {
            "id": "runtime_missing_file_basic",
            "category": "runtime",
            "target": "demo/broken_runtime.py",
            "args": ["--json"],
            "expected": {
              "result_present": true,
              "strategy_in": ["guard_exists", "try_except_recovery", "touch_only"],
              "sandbox_ok": true,
              "behavioral_ok": true
            }
          },
          {
            "id": "dependency_missing_import_basic",
            "category": "dependency",
            "target": "demo/broken_import.py",
            "args": ["--json"],
            "expected": {
              "result_present": true,
              "kind_in": ["dependency_install"]
            }
          },
          {
            "id": "shell_missing_command_basic",
            "category": "shell",
            "target": "demo/broken_shell_bat.txt",
            "args": ["--json"],
            "expected": {
              "result_present": true,
              "kind_in": ["shell_command_missing"]
            }
          },
          {
            "id": "cross_file_force_semantic_provider",
            "category": "cross_file",
            "target": "demo/cross_file_dep.py",
            "args": ["--json", "--force-semantic"],
            "expected": {
              "best_plan_present": true,
              "strategy_in": ["guard_exists", "try_except_recovery"],
              "provider_contains": ["helper_mod.py"],
              "caller_contains": ["cross_file_dep.py"],
              "target_file_contains": ["helper_mod.py"],
              "contract_ok": true
            }
          }
        ]
    """),
    "benchmarks/runner.py": textwrap.dedent("""\
        from __future__ import annotations

        import json
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


        def _json_load_loose(stdout: str) -> dict[str, Any] | None:
            text = stdout.strip()
            if not text:
                return None

            try:
                return json.loads(text)
            except Exception:
                pass

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                frag = text[start:end + 1]
                try:
                    return json.loads(frag)
                except Exception:
                    return None
            return None


        def _extract_strategy(payload: dict[str, Any]) -> str | None:
            best_plan = payload.get("best_plan") or {}
            evidence = best_plan.get("evidence") or {}
            if evidence.get("strategy"):
                return str(evidence["strategy"])

            result = payload.get("result") or {}
            metadata = result.get("metadata") or {}
            if metadata.get("strategy"):
                return str(metadata["strategy"])

            return None


        def _extract_kind(payload: dict[str, Any]) -> str | None:
            result = payload.get("result") or {}
            if result.get("kind"):
                return str(result["kind"])

            best_plan = payload.get("best_plan") or {}
            edits = best_plan.get("edits") or []
            if edits and isinstance(edits[0], dict) and edits[0].get("kind"):
                return str(edits[0]["kind"])

            return None


        def _extract_provider(payload: dict[str, Any]) -> str | None:
            best_plan = payload.get("best_plan") or {}
            evidence = best_plan.get("evidence") or {}
            provider = evidence.get("provider")
            if provider:
                return str(provider)

            planner = payload.get("planner") or {}
            best_plan2 = planner.get("best_plan") or {}
            evidence2 = best_plan2.get("evidence") or {}
            provider2 = evidence2.get("provider")
            if provider2:
                return str(provider2)

            return None


        def _extract_caller(payload: dict[str, Any]) -> str | None:
            best_plan = payload.get("best_plan") or {}
            evidence = best_plan.get("evidence") or {}
            caller = evidence.get("caller")
            if caller:
                return str(caller)

            planner = payload.get("planner") or {}
            best_plan2 = planner.get("best_plan") or {}
            evidence2 = best_plan2.get("evidence") or {}
            caller2 = evidence2.get("caller")
            if caller2:
                return str(caller2)

            return None


        def _extract_target_file(payload: dict[str, Any]) -> str | None:
            result = payload.get("result") or {}
            if result.get("target_file"):
                return str(result["target_file"])
            if result.get("file_path_hint"):
                return str(result["file_path_hint"])

            best_plan = payload.get("best_plan") or {}
            edits = best_plan.get("edits") or []
            if edits and isinstance(edits[0], dict) and edits[0].get("file"):
                return str(edits[0]["file"])

            return None


        def _extract_bool(payload: dict[str, Any], key: str) -> bool | None:
            value = payload.get(key)
            if isinstance(value, dict) and "ok" in value:
                return bool(value["ok"])
            return None


        def evaluate_case(case: FixtureCase) -> CaseResult:
            target_path = ROOT / case.target
            cmd = [str(TERMORGANISM_BIN), str(target_path.relative_to(ROOT))] + case.args

            t0 = time.perf_counter()
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 3)

            payload = _json_load_loose(proc.stdout)
            parsed_ok = payload is not None
            failure_reasons: list[str] = []
            extracted: dict[str, Any] = {}

            if not parsed_ok:
                failure_reasons.append("json_parse_failed")
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

            strategy = _extract_strategy(payload)
            kind = _extract_kind(payload)
            provider = _extract_provider(payload)
            caller = _extract_caller(payload)
            target_file = _extract_target_file(payload)
            sandbox_ok = _extract_bool(payload, "sandbox")
            contract_ok = _extract_bool(payload, "contract_result")
            behavioral_ok = _extract_bool(payload, "behavioral_verify")
            result_present = bool(payload.get("result"))
            best_plan_present = bool(payload.get("best_plan"))

            extracted = {
                "strategy": strategy,
                "kind": kind,
                "provider": provider,
                "caller": caller,
                "target_file": target_file,
                "sandbox_ok": sandbox_ok,
                "contract_ok": contract_ok,
                "behavioral_ok": behavioral_ok,
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
            lines.append("|---|---|---|---|---|---|---|---|---:|")
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
                    lines.append("")

            return "\\n".join(lines) + "\\n"


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
    """),
    "benchmarks/report_snippets.py": textwrap.dedent("""\
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
                "## Benchmark Snapshot\\n\\n"
                f"- Total cases: {s['total_cases']}\\n"
                f"- Success rate: {s['success_rate']:.2%}\\n"
                f"- Median fix time: {s['median_fix_time_ms']:.3f} ms\\n"
                f"- False positive rate: {s['false_positive_rate']:.2%}\\n"
            )


        if __name__ == "__main__":
            print(render_readme_snippet())
    """),
    "test_phase112_benchmark_harness.py": textwrap.dedent("""\
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
                "categories": sorted(payload["category_stats"].keys()),
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    """),
    "core/cli/autofix_cli.py": textwrap.dedent("""\
        from __future__ import annotations

        import argparse
        import json
        import os
        import platform
        import shutil
        import subprocess
        import sys
        from pathlib import Path

        from core.autofix import run_autofix


        def _shell_name() -> str:
            shell = os.environ.get("SHELL", "")
            return Path(shell).name if shell else "unknown"


        def _sandbox_mode() -> str:
            for name in ("bwrap", "firejail", "docker"):
                if shutil.which(name):
                    return name
            return "python-temp-workspace"


        def _local_model_hint() -> dict:
            hints = {
                "ollama": bool(shutil.which("ollama")),
                "llama_cpp_server": bool(shutil.which("llama-server")),
            }
            hints["available"] = any(hints.values())
            return hints


        def _dependency_health() -> dict:
            checks = {}
            for mod in ("json", "ast", "pathlib", "subprocess"):
                try:
                    __import__(mod)
                    checks[mod] = True
                except Exception:
                    checks[mod] = False
            checks["ok"] = all(checks.values())
            return checks


        def _workspace_health() -> dict:
            cwd = Path.cwd()
            probe = cwd / ".termorganism_write_probe"
            try:
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                writable = True
            except Exception:
                writable = False
            return {"cwd": str(cwd), "writable": writable}


        def command_doctor(as_json: bool = False) -> int:
            payload = {
                "ok": True,
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "shell": _shell_name(),
                "sandbox_mode": _sandbox_mode(),
                "local_model": _local_model_hint(),
                "dependency_health": _dependency_health(),
                "workspace": _workspace_health(),
            }
            payload["ok"] = bool(
                payload["dependency_health"]["ok"] and payload["workspace"]["writable"]
            )

            if as_json:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0

            print("TermOrganism Doctor")
            print("===================")
            print(f"Overall status : {'OK' if payload['ok'] else 'DEGRADED'}")
            print(f"Python         : {payload['python_version']}")
            print(f"Platform       : {payload['platform']}")
            print(f"Shell          : {payload['shell']}")
            print(f"Sandbox        : {payload['sandbox_mode']}")
            print(f"Local model    : {'available' if payload['local_model']['available'] else 'not detected'}")
            print(f"Dependencies   : {'ok' if payload['dependency_health']['ok'] else 'missing pieces'}")
            print(f"Workspace      : {'writable' if payload['workspace']['writable'] else 'not writable'}")
            return 0


        def build_parser() -> argparse.ArgumentParser:
            parser = argparse.ArgumentParser(prog="termorganism")
            sub = parser.add_subparsers(dest="command")

            doctor = sub.add_parser("doctor")
            doctor.add_argument("--json", action="store_true")

            repair = sub.add_parser("repair")
            repair.add_argument("target")
            repair.add_argument("--json", action="store_true")
            repair.add_argument("--force-semantic", action="store_true")
            repair.add_argument("--auto-apply", action="store_true")
            repair.add_argument("--exec", action="store_true")
            repair.add_argument("--dry-run", action="store_true")

            parser.add_argument("target", nargs="?")
            parser.add_argument("--json", action="store_true")
            parser.add_argument("--force-semantic", action="store_true")
            parser.add_argument("--auto-apply", action="store_true")
            parser.add_argument("--exec", action="store_true")
            parser.add_argument("--dry-run", action="store_true")

            return parser


        def _run_repair(target: str, args: argparse.Namespace) -> int:
            target_path = Path(target)
            if target_path.suffix == ".txt":
                error_text = target_path.read_text(encoding="utf-8", errors="replace")
                file_hint = str(target_path)
            else:
                if args.force_semantic:
                    error_text = "FORCED_SEMANTIC_ANALYSIS"
                else:
                    error_text = ""
                file_hint = str(target_path)

            result = run_autofix(
                error_text=error_text,
                file_path=file_hint,
                auto_apply=args.auto_apply,
                exec_suggestions=args.exec,
                dry_run=args.dry_run,
            )

            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0

            if not result.get("result"):
                print("No repair result produced.")
                return 0

            r = result["result"]
            print("TermOrganism Repair")
            print("===================")
            print(f"Summary       : {r.get('summary', '')}")
            print(f"Kind          : {r.get('kind', '')}")
            md = r.get("metadata") or {}
            if md.get("strategy"):
                print(f"Strategy      : {md.get('strategy')}")
            planner = result.get("planner") or {}
            best_plan = result.get("best_plan") or planner.get("best_plan") or {}
            evidence = best_plan.get("evidence") or {}
            if evidence.get("provider"):
                print(f"Provider      : {evidence.get('provider')}")
            if evidence.get("caller"):
                print(f"Caller        : {evidence.get('caller')}")
            sandbox = result.get("sandbox") or {}
            if isinstance(sandbox, dict):
                print(f"Sandbox       : {'ok' if sandbox.get('ok') else 'n/a'}")
            contract = result.get("contract_result") or {}
            if isinstance(contract, dict) and "ok" in contract:
                print(f"Contract      : {'ok' if contract.get('ok') else 'fail'}")
            behavioral = result.get("behavioral_verify") or {}
            if isinstance(behavioral, dict) and "ok" in behavioral:
                print(f"Behavioral    : {'ok' if behavioral.get('ok') else 'fail'}")
            return 0


        def main() -> int:
            parser = build_parser()
            args = parser.parse_args()

            if args.command == "doctor":
                return command_doctor(as_json=args.json)

            if args.command == "repair":
                return _run_repair(args.target, args)

            if args.target:
                return _run_repair(args.target, args)

            parser.print_help()
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    """),
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
