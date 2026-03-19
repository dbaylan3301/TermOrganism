#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/experts/file_runtime.py": '''from __future__ import annotations

import re
from pathlib import Path


class FileRuntimeExpert:
    name = "file_runtime"

    def _extract_missing_path(self, error_text: str) -> str | None:
        patterns = [
            r"No such file or directory: ['\\"]([^'\\"]+)['\\"]",
            r"FileNotFoundError: \\[Errno 2\\] No such file or directory: ['\\"]([^'\\"]+)['\\"]",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "")
            if m:
                return m.group(1)
        return None

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""
        missing_path = self._extract_missing_path(error_text)
        file_path = getattr(context, "file_path", None)

        if not missing_path:
            return [{
                "expert": self.name,
                "kind": "runtime_file_missing",
                "confidence": 0.30,
                "summary": "Missing file suspected but path could not be extracted",
                "patch": None,
                "candidate_code": "",
                "metadata": {},
            }]

        target = Path(missing_path)
        parent = str(target.parent) if str(target.parent) not in ("", ".") else ""

        shell_steps = []
        if parent:
            shell_steps.append(f"mkdir -p {parent}")
        shell_steps.append(f"touch {missing_path}")

        source_code = getattr(context, "source_code", "") or ""
        patched_code = source_code
        rationale = "create missing file path before read attempt"

        if source_code and "read_text()" in source_code and ".exists()" not in source_code:
            patched_code = source_code.replace(
                f'Path("{missing_path}").read_text()',
                f'Path("{missing_path}").read_text() if Path("{missing_path}").exists() else ""'
            )
            rationale = "guarded file read with exists() fallback"

        return [{
            "expert": self.name,
            "kind": "runtime_file_missing",
            "confidence": 0.82,
            "summary": f"Missing runtime file detected: {missing_path}",
            "patch": " && ".join(shell_steps),
            "candidate_code": patched_code,
            "file_path_hint": file_path,
            "missing_path": missing_path,
            "metadata": {
                "missing_path": missing_path,
                "parent_dir": parent,
                "shell_steps": shell_steps,
                "rationale": rationale,
            },
        }]
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

        if "filenotfounderror" in error_text or "no such file or directory" in error_text:
            experts.append("file_runtime")

        if (
            "permission denied" in error_text
            or "command not found" in error_text
            or "not found" in error_text
        ) and "no such file or directory" not in error_text:
            experts.append("shell_runtime")

        if not experts:
            experts.append("memory_retrieval")
            experts.append("llm_fallback")

        return experts


def route(context):
    return PolicyRouter().route(context)
''',

    "core/experts/__init__.py": '''from core.experts.dependency import DependencyExpert
from core.experts.file_runtime import FileRuntimeExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.shell_runtime import ShellRuntimeExpert

__all__ = [
    "DependencyExpert",
    "FileRuntimeExpert",
    "LLMFallbackExpert",
    "MemoryRetrievalExpert",
    "PythonSyntaxExpert",
    "ShellRuntimeExpert",
]
''',

    "core/autofix.py": '''from __future__ import annotations

from typing import Any

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.engine.router import PolicyRouter
from core.verify.sandbox import VerifierHub, run_in_sandbox
from core.verify.python_verify import verify_python
from core.memory import event_store, retrieval, stats

# expert references
from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.file_runtime import FileRuntimeExpert


class EventStoreAdapter:
    def append_event(self, payload: dict[str, Any]) -> None:
        if hasattr(event_store, "append_event"):
            event_store.append_event(payload)
            return
        if hasattr(event_store, "store_event"):
            event_store.store_event(payload)
            return
        if hasattr(event_store, "write_event"):
            event_store.write_event(payload)
            return

    def store_event(self, payload: dict[str, Any]) -> None:
        self.append_event(payload)

    def write_event(self, payload: dict[str, Any]) -> None:
        self.append_event(payload)


class RankerAdapter:
    def rank(self, candidates, context=None):
        if not isinstance(candidates, list):
            return candidates
        return sorted(
            candidates,
            key=lambda x: (
                x.get("confidence", 0.0) if isinstance(x, dict) else 0.0
            ),
            reverse=True,
        )

    def select_best(self, candidates, context=None):
        ranked = self.rank(candidates, context=context)
        if isinstance(ranked, list) and ranked:
            return ranked[0]
        return ranked


class ExpertAdapter:
    def __init__(self):
        self._registry = {
            "python_syntax": PythonSyntaxExpert(),
            "dependency": DependencyExpert(),
            "shell_runtime": ShellRuntimeExpert(),
            "memory_retrieval": MemoryRetrievalExpert(),
            "llm_fallback": LLMFallbackExpert(),
            "file_runtime": FileRuntimeExpert(),
        }

    def get(self, name: str):
        return self._registry[name]

    def resolve(self, names):
        return [self._registry[n] for n in names if n in self._registry]

    def keys(self):
        return list(self._registry.keys())

    def items(self):
        return self._registry.items()

    def __getitem__(self, key):
        return self._registry[key]


def _build_orchestrator() -> Orchestrator:
    router = PolicyRouter()
    experts = ExpertAdapter()
    verifier = VerifierHub()
    ranker = RankerAdapter()
    store = EventStoreAdapter()
    return Orchestrator(
        router=router,
        experts=experts,
        verifier=verifier,
        ranker=ranker,
        store=store,
    )


def _normalize_candidate(candidate):
    if isinstance(candidate, dict):
        return candidate

    # dataclass/repr-style candidates from python_syntax expert
    text = str(candidate)
    if "RepairCandidate(" in text:
        return {
            "expert": "python_syntax",
            "kind": "python_patch",
            "confidence": 0.85,
            "summary": text,
            "patch": None,
            "candidate_code": "",
            "raw_candidate": text,
        }

    return {
        "expert": "unknown",
        "kind": "unknown",
        "confidence": 0.0,
        "summary": text,
        "patch": None,
        "candidate_code": "",
        "raw_candidate": text,
    }


def _verify_candidate(candidate, context=None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""
    patch = c.get("patch", None)

    if kind in {"python_patch", "syntax"} and isinstance(code, str) and code.strip():
        return verify_python(code)

    if kind in {"dependency_install", "dependency"} or (
        isinstance(patch, str) and patch.strip().startswith("pip install ")
    ):
        return {
            "ok": True,
            "reason": "dependency install suggestion accepted as non-python command candidate",
            "mode": "dependency_install",
        }

    if kind in {"runtime_file_missing", "shell_command", "shell_runtime"}:
        return {
            "ok": True,
            "reason": "non-python operational fix; skipped python syntax verification",
            "mode": kind or "operational",
        }

    if isinstance(code, str) and code.strip():
        return verify_python(code)

    return {"ok": True, "reason": "no code payload"}


def _fallback_pipeline(error_text: str, file_path: str | None = None):
    context = build_context(error_text=error_text, file_path=file_path)
    router = PolicyRouter()
    routes = router.route(context)

    candidates = []
    registry = ExpertAdapter()

    for route_name in routes:
        expert = registry.get(route_name)
        if hasattr(expert, "propose"):
            try:
                proposals = expert.propose(context)
                if isinstance(proposals, list):
                    candidates.extend(proposals)
                elif proposals is not None:
                    candidates.append(proposals)
            except Exception as e:
                candidates.append({
                    "expert": route_name,
                    "kind": "expert_failure",
                    "confidence": 0.0,
                    "summary": f"expert failure: {type(e).__name__}: {e}",
                    "patch": None,
                    "candidate_code": "",
                })

    ranker = RankerAdapter()
    ranked = ranker.rank(candidates, context=context)
    best = ranked[0] if isinstance(ranked, list) and ranked else None

    verify_result = _verify_candidate(best, context=context)
    sandbox_result = run_in_sandbox(best, context)

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "routes": routes,
        "candidates": candidates,
        "best": best,
        "verify": verify_result,
        "sandbox": sandbox_result,
    }

    EventStoreAdapter().append_event(payload)

    return {
        "result": best,
        "routes": routes,
        "verify": verify_result,
        "sandbox": sandbox_result,
    }


def run_autofix(error_text: str, file_path: str | None = None):
    context = build_context(error_text=error_text, file_path=file_path)

    try:
        orchestrator = _build_orchestrator()
        result = orchestrator.run(context)
    except Exception:
        return _fallback_pipeline(error_text=error_text, file_path=file_path)

    verify_result = _verify_candidate(result, context=context)
    sandbox_result = run_in_sandbox(result, context)

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "result": result,
        "verify": verify_result,
        "sandbox": sandbox_result,
    }

    try:
        EventStoreAdapter().append_event(payload)
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
        backup.write_text(
            path.read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
        )
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
