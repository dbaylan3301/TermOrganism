#!/usr/bin/env python3
from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
DEMO = ROOT / "demo"
EVENTS = ROOT / "memory" / "TermOrganism" / "repair_events.jsonl"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def tail_jsonl(path: Path, n: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"_raw": line, "_parse_error": True})
    return out


def maybe_get_router():
    try:
        from core.engine.router import PolicyRouter
        return PolicyRouter()
    except Exception:
        return None


def maybe_build_context():
    from core.engine.context_builder import build_context
    return build_context


def maybe_run_autofix():
    from core.autofix import run_autofix
    return run_autofix


def detect_error_text_for_fixture(path: Path) -> str:
    name = path.name

    if name == "broken_syntax.py":
        return (
            'Traceback (most recent call last):\\n'
            f'  File "{path}", line 1\\n'
            '    def add(a, b)\\n'
            '                 ^\\n'
            "SyntaxError: expected ':'"
        )

    if name == "broken_import.py":
        return (
            "Traceback (most recent call last):\\n"
            f'  File "{path}", line 1, in <module>\\n'
            "    import definitely_missing_package_12345\\n"
            "ModuleNotFoundError: No module named 'definitely_missing_package_12345'"
        )

    if name == "broken_runtime.py":
        return (
            "Traceback (most recent call last):\\n"
            f'  File "{path}", line 3, in <module>\\n'
            '    print(Path("logs/app.log").read_text())\\n'
            "FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'"
        )

    if name == "broken_shell.txt":
        return read_text(path)

    return f"Unknown error fixture for {path.name}"


def expected_route(error_text: str) -> list[str]:
    router = maybe_get_router()
    if router is None:
        return ["<router unavailable>"]

    try:
        build_context = maybe_build_context()
        ctx = build_context(error_text=error_text, file_path=None)
        return router.route(ctx)
    except Exception as e:
        return [f"<route failed: {type(e).__name__}: {e}>"]


def run_one(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "fixture": path.name,
        "ok": False,
    }

    error_text = detect_error_text_for_fixture(path)
    result["error_text"] = error_text
    result["predicted_route"] = expected_route(error_text)

    try:
        run_autofix = maybe_run_autofix()
        autofix_result = run_autofix(error_text=error_text, file_path=str(path))
        result["autofix_result"] = autofix_result
        result["ok"] = True
    except Exception as e:
        result["exception"] = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }

    result["event_tail"] = tail_jsonl(EVENTS, n=3)
    return result


def print_report(report: list[dict[str, Any]]) -> None:
    print("=" * 80)
    print("TermOrganism Integration Test Report")
    print("=" * 80)

    for item in report:
        print(f"\\n[CASE] {item['fixture']}")
        print(f"  ok: {item['ok']}")
        print(f"  predicted_route: {item.get('predicted_route')}")

        if item.get("ok"):
            ar = item.get("autofix_result")
            print(f"  autofix_result_type: {type(ar).__name__}")
            print(f"  autofix_result: {json.dumps(ar, ensure_ascii=False, default=str, indent=2)}")
        else:
            ex = item.get("exception", {})
            print(f"  exception: {ex.get('type')}: {ex.get('message')}")

        tail = item.get("event_tail", [])
        print(f"  memory_tail_count: {len(tail)}")
        if tail:
            print("  memory_tail_last:")
            print(json.dumps(tail[-1], ensure_ascii=False, default=str, indent=2))

    print("\\n" + "=" * 80)


def main() -> int:
    fixtures = [
        DEMO / "broken_syntax.py",
        DEMO / "broken_import.py",
        DEMO / "broken_runtime.py",
        DEMO / "broken_shell.txt",
    ]

    missing = [str(p) for p in fixtures if not p.exists()]
    if missing:
        print("Eksik fixture dosyaları:")
        for m in missing:
            print(" -", m)
        print("\\nÖnce create_integration_fixtures.py çalıştır.")
        return 1

    report = [run_one(p) for p in fixtures]
    print_report(report)

    failures = sum(1 for x in report if not x.get("ok"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
