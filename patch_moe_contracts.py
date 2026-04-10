from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()

FILES = {
    "core/engine/context_builder.py": '''from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepairContext:
    error_text: str
    file_path: str | None = None
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""


def build_context(
    error_text: str,
    file_path: str | None = None,
    stdout: str = "",
    stderr: str = "",
    traceback: str = "",
) -> RepairContext:
    return RepairContext(
        error_text=error_text,
        file_path=file_path,
        stdout=stdout,
        stderr=stderr,
        traceback=traceback,
    )
''',

    "core/engine/router.py": '''from __future__ import annotations


class PolicyRouter:
    def route(self, context):
        error_text = (getattr(context, "error_text", "") or "").lower()
        experts: list[str] = []

        if "syntaxerror" in error_text or "indentationerror" in error_text:
            experts.append("python_syntax")

        if "modulenotfounderror" in error_text or "no module named" in error_text:
            experts.append("dependency")

        if (
            "permission denied" in error_text
            or "command not found" in error_text
            or "not found" in error_text
        ):
            experts.append("shell_runtime")

        if not experts:
            experts.append("memory_retrieval")
            experts.append("llm_fallback")

        return experts


def route(context):
    return PolicyRouter().route(context)
''',

    "core/autofix.py": '''from __future__ import annotations

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.verify.python_verify import verify_python
from core.verify.sandbox import run_in_sandbox
from core.memory import event_store
from core.memory import retrieval, stats

# expert references for orchestration visibility
from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert


def run_autofix(error_text: str, file_path: str | None = None):
    context = build_context(error_text=error_text, file_path=file_path)

    orchestrator = Orchestrator()
    result = orchestrator.run(context)

    candidate_code = ""
    if isinstance(result, dict):
        candidate_code = result.get("candidate_code", "") or ""

    verify_result = (
        verify_python(candidate_code)
        if candidate_code
        else {"ok": True, "reason": "no code payload"}
    )
    sandbox_result = run_in_sandbox(result, context)

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "verify": verify_result,
        "sandbox": sandbox_result,
        "result": result,
    }

    try:
        if hasattr(event_store, "append_event"):
            event_store.append_event(payload)
        elif hasattr(event_store, "store_event"):
            event_store.store_event(payload)
    except Exception:
        pass

    return {
        "result": result,
        "verify": verify_result,
        "sandbox": sandbox_result,
    }
''',
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


def compile_check() -> int:
    targets = [
        "core/engine/context_builder.py",
        "core/engine/router.py",
        "core/autofix.py",
    ]
    cmd = [sys.executable, "-m", "py_compile", *targets]
    print("\\n[RUN]    " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def run_smoke() -> int:
    smoke = ROOT / "smoke_test_termorganism.py"
    if not smoke.exists():
        print("[WARN]   smoke_test_termorganism.py bulunamadı, test atlandı.")
        return 0

    cmd = [sys.executable, str(smoke)]
    print("\\n[RUN]    " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    for rel_path, content in FILES.items():
        backup_and_write(rel_path, content)

    rc = compile_check()
    if rc != 0:
        print("\\n[FAIL]   py_compile başarısız.")
        return rc

    print("\\n[OK]     py_compile başarılı.")
    return run_smoke()


if __name__ == "__main__":
    raise SystemExit(main())
