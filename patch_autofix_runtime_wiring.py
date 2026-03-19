#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
TARGET = ROOT / "core" / "autofix.py"

content = r'''from __future__ import annotations

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
                    "confidence": 0.0,
                    "summary": f"expert failure: {type(e).__name__}: {e}",
                    "patch": None,
                })

    ranker = RankerAdapter()
    ranked = ranker.rank(candidates, context=context)
    best = ranked[0] if isinstance(ranked, list) and ranked else None

    candidate_code = ""
    if isinstance(best, dict):
        candidate_code = best.get("candidate_code", "") or best.get("patch", "") or ""

    verify_result = (
        verify_python(candidate_code)
        if candidate_code and isinstance(candidate_code, str)
        else {"ok": True, "reason": "no code payload"}
    )

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
        # constructor/run contract mismatch olursa sistem yine düşmesin
        return _fallback_pipeline(error_text=error_text, file_path=file_path)

    candidate_code = ""
    if isinstance(result, dict):
        candidate_code = result.get("candidate_code", "") or result.get("patch", "") or ""

    verify_result = (
        verify_python(candidate_code)
        if candidate_code and isinstance(candidate_code, str)
        else {"ok": True, "reason": "no code payload"}
    )
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
'''

backup = TARGET.with_suffix(".py.bak")
if TARGET.exists():
    backup.write_text(TARGET.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    print(f"[BACKUP] {backup}")

TARGET.write_text(content, encoding="utf-8")
print(f"[WRITE] {TARGET}")
