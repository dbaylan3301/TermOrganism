from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


JS_EXTS = {".js", ".jsx", ".mjs", ".cjs"}
TS_EXTS = {".ts", ".tsx"}
ALL_EXTS = JS_EXTS | TS_EXTS


def is_javascript_path(file_path: str | None) -> bool:
    if not file_path:
        return False
    return Path(str(file_path)).suffix.lower() in ALL_EXTS


def _run_cmd(cmd: list[str], cwd: str | None = None, timeout: int = 5) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "cmd": cmd,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": f"command not found: {cmd[0]}",
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": 124,
            "stdout": "",
            "stderr": "timeout",
            "cmd": cmd,
        }


def verify_javascript_candidate(
    *,
    code: str,
    target_file: str | None,
    project_root: str | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    ext = Path(str(target_file or "candidate.js")).suffix.lower()
    if ext not in ALL_EXTS:
        ext = ".js"

    with tempfile.TemporaryDirectory(prefix="termorganism_js_verify_") as td:
        temp_path = Path(td) / f"candidate{ext}"
        temp_path.write_text(code, encoding="utf-8")

        result: dict[str, Any] = {
            "ok": False,
            "language": "typescript" if ext in TS_EXTS else "javascript",
            "temp_path": str(temp_path),
            "checks": {},
            "duration_ms": 0.0,
        }

        # Node syntax check for JS-like files
        node_available = shutil.which("node") is not None
        eslint_available = shutil.which("eslint") is not None
        tsc_available = shutil.which("tsc") is not None

        if ext in JS_EXTS:
            if node_available:
                result["checks"]["node_check"] = _run_cmd(["node", "--check", str(temp_path)], timeout=5)
            else:
                result["checks"]["node_check"] = {
                    "ok": False,
                    "returncode": 127,
                    "stdout": "",
                    "stderr": "node not available",
                    "cmd": ["node", "--check", str(temp_path)],
                }

        # TSC noEmit for TS-like files if available
        if ext in TS_EXTS:
            if tsc_available:
                result["checks"]["tsc_no_emit"] = _run_cmd(["tsc", "--noEmit", str(temp_path)], timeout=8)
            else:
                result["checks"]["tsc_no_emit"] = {
                    "ok": False,
                    "returncode": 127,
                    "stdout": "",
                    "stderr": "tsc not available",
                    "cmd": ["tsc", "--noEmit", str(temp_path)],
                }

        # ESLint optional: only advisory
        if eslint_available:
            result["checks"]["eslint"] = _run_cmd(["eslint", str(temp_path)], cwd=project_root, timeout=8)
        else:
            result["checks"]["eslint"] = {
                "ok": False,
                "returncode": 127,
                "stdout": "",
                "stderr": "eslint not available",
                "cmd": ["eslint", str(temp_path)],
            }

        # scoring
        primary_ok = False
        if ext in JS_EXTS:
            primary_ok = bool((result["checks"].get("node_check") or {}).get("ok"))
        elif ext in TS_EXTS:
            primary_ok = bool((result["checks"].get("tsc_no_emit") or {}).get("ok"))

        eslint_ok = bool((result["checks"].get("eslint") or {}).get("ok"))
        score = 0.2
        if primary_ok:
            score = 0.75
        if primary_ok and eslint_ok:
            score = 0.88

        result["ok"] = primary_ok
        result["confidence"] = score
        result["duration_ms"] = round((time.perf_counter() - start) * 1000.0, 3)
        return result
