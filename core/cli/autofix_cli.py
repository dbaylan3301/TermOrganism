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
from core.ui.thoughts import AsyncThoughtBus, build_thought_sink


import faulthandler
import re
import tempfile
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
    repair.add_argument("--think", action="store_true")
    repair.add_argument("--think-jsonl", default=None)

    return parser



def _verify_runtime_fallback_candidate(target_path: Path, code: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="termorganism_cli_verify_") as tmpdir:
        tmpdir = Path(tmpdir)
        candidate = tmpdir / target_path.name
        candidate.write_text(code, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, candidate.name],
            cwd=str(tmpdir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }


def _build_runtime_fallback_candidate(target_path: Path) -> tuple[str | None, str | None]:
    source = target_path.read_text(encoding="utf-8", errors="replace")

    # 1) JSON/config missing file -> safe default {}
    json_pat = re.compile(
        r'^(?P<indent>[ \t]*)with open\((?P<q>["\'])(?P<path>.+?)(?P=q),\s*["\']r["\'](?:,\s*encoding=["\']utf-8["\'])?\) as (?P<fh>\w+):\n(?P=indent)[ \t]+(?P<var>\w+)\s*=\s*json\.load\((?P=fh)\)',
        flags=re.M,
    )
    m = json_pat.search(source)
    if m:
        indent = m.group("indent")
        missing_path = m.group("path")
        varname = m.group("var")
        repl = (
            f'{indent}try:\n'
            f'{indent}    with open("{missing_path}", "r", encoding="utf-8") as f:\n'
            f'{indent}        {varname} = json.load(f)\n'
            f'{indent}except FileNotFoundError:\n'
            f'{indent}    {varname} = {{}}'
        )
        code = source[:m.start()] + repl + source[m.end():]
        return (f"Recover missing JSON/config file with empty default: {missing_path}", code)

    # 2) Missing parent dir on write/append
    write_pat = re.compile(
        r'^(?P<indent>[ \t]*)(?P<stmt>with open\((?P<q>["\'])(?P<path>.+?)(?P=q),\s*["\'](?P<mode>[wa])["\'](?:,\s*encoding=["\']utf-8["\'])?\)\s+as\s+\w+\s*:)',
        flags=re.M,
    )
    m = write_pat.search(source)
    if m:
        indent = m.group("indent")
        missing_path = m.group("path")
        parent = str(Path(missing_path).parent).replace("\\", "/")
        if parent and parent != ".":
            insert = f'{indent}Path("{parent}").mkdir(parents=True, exist_ok=True)\n'
            code = source[:m.start()] + insert + source[m.start():]
            if "from pathlib import Path" not in code:
                code = "from pathlib import Path\n" + code
            return (f"Create parent directory before file write: {missing_path}", code)

    return (None, None)


def _run_repair(target: str, args: argparse.Namespace) -> int:
    target_path = Path(target).resolve()

    if not target_path.exists():
        print(f"error: target does not exist: {target_path}", file=sys.stderr)
        return 2

    error_text = ""
    if args.force_semantic:
        error_text = "FORCED_SEMANTIC_ANALYSIS"
    elif target_path.suffix == ".py":
        try:
            proc = subprocess.run(
                [sys.executable, target_path.name],
                cwd=str(target_path.parent),
                capture_output=True,
                text=True,
                timeout=8,
            )
            error_text = (proc.stderr or proc.stdout or "").strip()
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
    elif target_path.suffix == ".txt":
        try:
            proc = subprocess.run(
                ["bash", str(target_path)],
                cwd=str(target_path.parent),
                capture_output=True,
                text=True,
                timeout=8,
            )
            error_text = (proc.stderr or proc.stdout or "").strip()
        except Exception:
            error_text = target_path.read_text(encoding="utf-8", errors="replace")

        if not error_text:
            error_text = target_path.read_text(encoding="utf-8", errors="replace")
    else:
        error_text = ""

    sink = build_thought_sink(
        enable_live=args.think,
        jsonl_path=args.think_jsonl,
    )
    bus = AsyncThoughtBus(sink) if sink is not None else None

    try:
        result = run_autofix(
            error_text=error_text,
            file_path=str(target_path),
            auto_apply=args.auto_apply,
            exec_suggestions=args.exec,
            dry_run=args.dry_run,
            thought_bus=bus,
        )
    finally:
        if bus is not None:
            bus.close()

    if isinstance(result, dict):
        behavioral = result.get("behavioral_verify")
        if result.get("sandbox") is None and isinstance(behavioral, dict):
            result["sandbox"] = behavioral

        rr = result.get("result")
        if isinstance(rr, dict):
            err_l = error_text.lower()
            summary_l = str(rr.get("summary") or "").lower()

            if "modulenotfounderror" in err_l or "no module named" in err_l:
                rr["kind"] = "dependency_install"
            elif "command not found" in err_l or "shell command not found" in summary_l:
                rr["kind"] = "shell_command_missing"
            elif "filenotfounderror" in err_l or "no such file or directory" in err_l:
                rr["kind"] = "runtime_file_missing"


    if isinstance(result, dict) and target_path.suffix == ".py":
        sandbox = result.get("sandbox") if isinstance(result.get("sandbox"), dict) else {}
        behavioral = result.get("behavioral_verify") if isinstance(result.get("behavioral_verify"), dict) else {}

        if not sandbox.get("ok") or not behavioral.get("ok"):
            summary, fallback_code = _build_runtime_fallback_candidate(target_path)
            if fallback_code:
                verify = _verify_runtime_fallback_candidate(target_path, fallback_code)
                if verify.get("ok"):
                    result["sandbox"] = {
                        "ok": True,
                        "reason": "cli runtime fallback verification passed",
                        "runtime": verify,
                    }
                    result["behavioral_verify"] = {
                        "ok": True,
                        "reason": "cli runtime fallback verification passed",
                        "runtime": verify,
                    }
                    result["contract_result"] = {
                        "ok": True,
                        "reason": "cli runtime fallback verification passed",
                        "score": 1.0,
                        "checks": [
                            {"name": "exit_code", "ok": True, "actual": 0},
                        ],
                    }

                    rr = result.get("result")
                    if isinstance(rr, dict):
                        rr["summary"] = summary
                        rr["candidate_code"] = fallback_code
                        rr["kind"] = "runtime_file_missing"
                        rr["target_file"] = str(target_path)
                        rr["file_path_hint"] = str(target_path)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main() -> int:

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "doctor":
        return command_doctor(as_json=args.json)

    if args.command == "repair":
        return _run_repair(args.target, args)

    parser.print_usage(sys.stderr)
    print("error: missing command", file=sys.stderr)
    return 2


if __name__ == "__main__":

    raise SystemExit(main())
