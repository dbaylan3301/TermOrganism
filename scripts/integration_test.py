#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOCKET = Path("/tmp/termorganism.sock")


def wait_for_socket(timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if SOCKET.exists():
            return True
        time.sleep(0.05)
    return False


def prepare_fixtures():
    Path("/tmp/broken_runtime_hotforce.py").write_text(
        'print(open("logs/app.log").read())\n',
        encoding="utf-8",
    )
    Path("/tmp/broken_import_hotforce.py").write_text(
        'import definitely_missing_package_12345\n',
        encoding="utf-8",
    )
    Path("/tmp/fallback_case.py").write_text(
        'import definitely_missing_package_beta as dmp\nprint(dmp)\n',
        encoding="utf-8",
    )


def start_daemon():
    try:
        SOCKET.unlink(missing_ok=True)
    except Exception:
        pass

    proc = subprocess.Popen(
        [sys.executable, "-m", "core.daemon.server"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if not wait_for_socket():
        proc.terminate()
        raise RuntimeError("daemon socket did not appear")
    return proc


def run_json(cmd: str) -> tuple[bool, dict | None, str]:
    res = subprocess.run(
        cmd,
        cwd=str(ROOT),
        shell=True,
        capture_output=True,
        text=True,
    )
    stdout = res.stdout.strip()
    if not stdout:
        return False, None, "empty stdout"
    try:
        data = json.loads(stdout)
        return True, data, ""
    except Exception as e:
        return False, None, f"json parse failed: {e}; stdout={stdout[:300]}"


def require(data: dict, path: list[str], expected=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            raise AssertionError(f"missing path: {'.'.join(path)}")
        cur = cur[key]
    if expected is not None and cur != expected:
        raise AssertionError(f"path {'.'.join(path)} expected={expected!r} actual={cur!r}")
    return cur


def run_test(name: str, cmd: str, checker):
    print(f"\n{'='*60}")
    print(name)
    print(f"{'='*60}")

    start = time.time()
    ok, data, err = run_json(cmd)
    elapsed = (time.time() - start) * 1000.0

    if not ok or data is None:
        print(f"FAIL: {err}")
        return False

    try:
        checker(data)
    except Exception as e:
        print("FAIL:", e)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1200])
        return False

    print(f"PASS in {elapsed:.1f}ms")
    print(f"mode={data.get('mode')}")
    if "daemon" in data:
        print(f"daemon_ms={data['daemon'].get('request_ms')}")
    if "workspace_pool" in data:
        print(f"workspace_pool={data['workspace_pool']}")
    if "fast_v2" in data:
        print(f"fast_v2={data['fast_v2']}")
    print(f"fallback_chain={data.get('fallback_chain')}")
    return True


def check_hot_force_runtime(data: dict):
    require(data, ["success"], True)
    require(data, ["mode"], "hot_force_path")
    require(data, ["signature"], "filenotfounderror:open:runtime")
    require(data, ["verify", "ok"], True)
    require(data, ["workspace_pool", "source"], "pool")
    require(data, ["fallback_chain"], ["hot_force"])


def check_hot_force_import(data: dict):
    require(data, ["success"], True)
    require(data, ["mode"], "hot_force_path")
    require(data, ["signature"], "importerror:no_module_named")
    require(data, ["strategy"], "import_guard")
    require(data, ["verify", "ok"], True)
    require(data, ["workspace_pool", "source"], "pool")
    require(data, ["fallback_chain"], ["hot_force"])


def check_fallback_fast_shortcut(data: dict):
    require(data, ["success"], True)
    require(data, ["mode"], "fast_shortcut")
    require(data, ["signature"], "importerror:no_module_named")
    require(data, ["strategy"], "import_guard")
    require(data, ["verify", "ok"], True)
    require(data, ["workspace_pool", "source"], "pool")
    require(data, ["fast_v2", "used"], True)
    require(data, ["fallback_chain"], ["hot_force_failed", "fast"])


def main() -> int:
    prepare_fixtures()
    daemon = start_daemon()

    tests = [
        (
            "Hot Force Runtime",
            "TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_runtime_hotforce.py --json 2>/dev/null",
            check_hot_force_runtime,
        ),
        (
            "Hot Force Import",
            "TERMORGANISM_USE_DAEMON=1 TERMORGANISM_HOT_FORCE=1 ./termorganism repair /tmp/broken_import_hotforce.py --json 2>/dev/null",
            check_hot_force_import,
        ),
        (
            "Fallback Fast Shortcut",
            "TERMORGANISM_USE_DAEMON=1 ./termorganism repair /tmp/fallback_case.py --json 2>/dev/null",
            check_fallback_fast_shortcut,
        ),
    ]

    results = []
    try:
        for name, cmd, checker in tests:
            results.append((name, run_test(name, cmd, checker)))
    finally:
        daemon.terminate()
        try:
            daemon.wait(timeout=3)
        except Exception:
            daemon.kill()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, ok in results:
        print(("PASS" if ok else "FAIL"), "-", name)

    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
