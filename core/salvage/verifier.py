from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

def verify_candidate(candidate_source: str, original_path: str) -> dict:
    ast_ok = False
    ast_error = None
    try:
        ast.parse(candidate_source)
        ast_ok = True
    except SyntaxError as exc:
        ast_error = f"{exc.__class__.__name__}: {exc}"

    with tempfile.TemporaryDirectory(prefix="termorganism_salvage_") as td:
        p = Path(td) / Path(original_path).name
        p.write_text(candidate_source, encoding="utf-8")

        compile_proc = subprocess.run(
            [sys.executable, "-m", "py_compile", str(p)],
            capture_output=True,
            text=True,
        )
        compile_ok = compile_proc.returncode == 0

        smoke = {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }
        try:
            proc = subprocess.run(
                [sys.executable, str(p)],
                capture_output=True,
                text=True,
                timeout=3,
            )
            smoke = {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout[:1200],
                "stderr": proc.stderr[:1200],
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            smoke = {
                "ok": False,
                "returncode": None,
                "stdout": (exc.stdout or "")[:1200] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[:1200] if isinstance(exc.stderr, str) else "",
                "timed_out": True,
            }

    smoke_ok = bool(smoke.get("ok"))
    overall_ok = bool(ast_ok and compile_ok and smoke_ok)

    if overall_ok:
        repair_quality = "smoke_passed"
    elif ast_ok and compile_ok:
        repair_quality = "compile_only"
    elif ast_ok:
        repair_quality = "syntax_only"
    else:
        repair_quality = "failed"

    return {
        "ast_ok": ast_ok,
        "ast_error": ast_error,
        "compile_ok": compile_ok,
        "compile_stderr": compile_proc.stderr[:1200],
        "smoke_run": smoke,
        "smoke_ok": smoke_ok,
        "repair_quality": repair_quality,
        "overall_ok": overall_ok,
    }
