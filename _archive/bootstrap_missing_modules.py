from pathlib import Path

ROOT = Path.cwd()

files = {
    "core/autofix.py": '''from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator

def run_autofix(error_text: str, file_path: str | None = None):
    ctx = build_context(error_text=error_text, file_path=file_path)
    orch = Orchestrator()
    return orch.run(ctx)
''',

    "core/engine/router.py": '''def route(context):
    error_text = (getattr(context, "error_text", "") or "").lower()

    experts = []

    if "syntaxerror" in error_text or "indentationerror" in error_text:
        experts.append("python_syntax")

    if "modulenotfounderror" in error_text or "no module named" in error_text:
        experts.append("dependency")

    if "permission denied" in error_text or "not found" in error_text:
        experts.append("shell_runtime")

    if not experts:
        experts.append("llm_fallback")

    return experts
''',

    "core/experts/llm_fallback.py": '''class LLMFallbackExpert:
    name = "llm_fallback"

    def propose(self, context):
        return [{
            "expert": self.name,
            "confidence": 0.25,
            "summary": "Fallback heuristic proposal",
            "patch": None,
        }]
''',

    "core/experts/memory_retrieval.py": '''class MemoryRetrievalExpert:
    name = "memory_retrieval"

    def propose(self, context):
        return [{
            "expert": self.name,
            "confidence": 0.35,
            "summary": "Retrieved similar repair memories",
            "patch": None,
        }]
''',

    "core/experts/shell_runtime.py": '''class ShellRuntimeExpert:
    name = "shell_runtime"

    def propose(self, context):
        return [{
            "expert": self.name,
            "confidence": 0.40,
            "summary": "Shell/runtime oriented repair suggestion",
            "patch": None,
        }]
''',

    "core/util/logging.py": '''from datetime import datetime

def log_event(message: str):
    print(f"[TermOrganism {datetime.utcnow().isoformat()}] {message}")
''',

    "core/verify/python_verify.py": '''import ast

def verify_python(code: str):
    try:
        ast.parse(code)
        return {"ok": True, "reason": "AST parse ok"}
    except Exception as e:
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
''',

    "core/verify/sandbox.py": '''def run_in_sandbox(candidate, context=None):
    return {
        "ok": True,
        "reason": "sandbox stub passed",
        "candidate": candidate,
    }
''',
}

for rel, content in files.items():
    path = ROOT / rel
    if path.exists():
        print(f"[SKIP] exists: {rel}")
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[CREATE] {rel}")

print("\\nDone.")
