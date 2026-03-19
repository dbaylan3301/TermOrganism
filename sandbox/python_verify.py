from __future__ import annotations

import py_compile
import subprocess
import tempfile
from pathlib import Path

from core.models.schemas import FailureContext, RepairCandidate, VerificationResult


class PythonVerifier:
    def verify(self, ctx: FailureContext, candidate: RepairCandidate, timeout: int = 5) -> VerificationResult:
        if candidate.patched_code is None:
            return VerificationResult(False, False, False, False, 0.0, "", "candidate has no patched code")

        with tempfile.TemporaryDirectory(prefix="termorganism-") as tmpdir:
            tmp_path = Path(tmpdir) / Path(ctx.file_path).name
            tmp_path.write_text(candidate.patched_code, encoding="utf-8")

            compile_ok = True
            compile_stderr = ""
            try:
                py_compile.compile(str(tmp_path), doraise=True)
            except py_compile.PyCompileError as exc:
                compile_ok = False
                compile_stderr = str(exc)

            run_ok = False
            run_stdout = ""
            run_stderr = compile_stderr
            if compile_ok:
                proc = subprocess.run(
                    ["python3", str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                run_stdout = proc.stdout
                run_stderr = proc.stderr
                run_ok = proc.returncode == 0

            score = 0.0
            if compile_ok:
                score += 0.55
            if run_ok:
                score += 0.35
            tests_ok = False
            if ctx.project_facts.get("requirements.txt") or ctx.project_facts.get("pyproject.toml"):
                score += 0.05
            if candidate.patch_safety_score:
                score += min(0.05, candidate.patch_safety_score * 0.05)

            ok = compile_ok and run_ok
            return VerificationResult(
                ok=ok,
                compile_ok=compile_ok,
                run_ok=run_ok,
                tests_ok=tests_ok,
                score=min(score, 1.0),
                stdout=run_stdout,
                stderr=run_stderr,
                metrics={"timeout": timeout},
            )
