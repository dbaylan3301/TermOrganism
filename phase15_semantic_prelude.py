#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()
TARGET = ROOT / "core" / "autofix.py"

NEW_CONTENT = r'''from __future__ import annotations

from typing import Any
import ast
import re

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.engine.router import PolicyRouter
from core.verify.sandbox import VerifierHub, run_in_sandbox
from core.verify.python_verify import verify_python
from core.memory import event_store, retrieval, stats
from core.util.patch_apply import make_backup, apply_text_replacement, restore_backup
from core.util.safe_exec import execute_safe_suggestions
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions

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
    def _score(self, candidate):
        if isinstance(candidate, dict):
            return candidate.get("confidence", 0.0)
        return getattr(candidate, "confidence", 0.0)

    def rank(self, candidates, context=None):
        if not isinstance(candidates, list):
            return candidates
        return sorted(candidates, key=self._score, reverse=True)

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


def _extract_field(text: str, field: str):
    patterns = [
        rf"{field}='((?:[^'\\\\]|\\\\.)*)'",
        rf'{field}="((?:[^"\\\\]|\\\\.)*)"',
        rf"{field}=([0-9]+(?:\.[0-9]+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            raw = m.group(1)
            try:
                return ast.literal_eval(f"'{raw}'")
            except Exception:
                try:
                    return float(raw) if "." in raw or raw.isdigit() else raw
                except Exception:
                    return raw
    return None


def _normalize_candidate(candidate):
    if isinstance(candidate, dict):
        c = dict(candidate)
        if "kind" not in c:
            patch = c.get("patch")
            if isinstance(patch, str) and patch.startswith("pip install "):
                c["kind"] = "dependency_install"
            elif c.get("expert") == "file_runtime":
                c["kind"] = "runtime_file_missing"
            else:
                c["kind"] = ""
        if "confidence" not in c:
            c["confidence"] = 0.0
        if "candidate_code" not in c:
            c["candidate_code"] = ""
        return c

    attrs = {}
    for name in (
        "expert_name",
        "kind",
        "patched_code",
        "patch_unified_diff",
        "rationale",
        "router_score",
        "expert_score",
        "memory_prior",
        "patch_safety_score",
        "metadata",
    ):
        if hasattr(candidate, name):
            attrs[name] = getattr(candidate, name)

    if attrs:
        return {
            "expert": attrs.get("expert_name", "unknown"),
            "kind": attrs.get("kind", ""),
            "confidence": attrs.get("expert_score", 0.0),
            "summary": attrs.get("rationale", ""),
            "patch": attrs.get("patch_unified_diff"),
            "candidate_code": attrs.get("patched_code", "") or "",
            "raw_candidate": str(candidate),
            "metadata": attrs.get("metadata", {}) or {},
            "router_score": attrs.get("router_score", 0.0),
            "expert_score": attrs.get("expert_score", 0.0),
            "memory_prior": attrs.get("memory_prior", 0.0),
            "patch_safety_score": attrs.get("patch_safety_score", 0.0),
        }

    text = str(candidate)
    if "RepairCandidate(" in text:
        expert = _extract_field(text, "expert_name") or "python_syntax"
        kind = _extract_field(text, "kind") or "python_patch"
        patched_code = _extract_field(text, "patched_code") or ""
        patch_unified_diff = _extract_field(text, "patch_unified_diff")
        rationale = _extract_field(text, "rationale") or text
        expert_score = _extract_field(text, "expert_score") or 0.0
        router_score = _extract_field(text, "router_score") or 0.0
        memory_prior = _extract_field(text, "memory_prior") or 0.0
        patch_safety_score = _extract_field(text, "patch_safety_score") or 0.0

        return {
            "expert": expert,
            "kind": kind,
            "confidence": expert_score,
            "summary": rationale,
            "patch": patch_unified_diff,
            "candidate_code": patched_code,
            "raw_candidate": text,
            "metadata": {},
            "router_score": router_score,
            "expert_score": expert_score,
            "memory_prior": memory_prior,
            "patch_safety_score": patch_safety_score,
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


def _normalize_candidates(candidates):
    if not isinstance(candidates, list):
        return candidates
    return [_normalize_candidate(c) for c in candidates]


def _build_semantic_prelude(error_text: str, file_path: str | None):
    if file_path and str(file_path).endswith(".py"):
        try:
            repro = run_python_file(file_path)
        except Exception as e:
            repro = {
                "ok": False,
                "command": [],
                "cwd": "",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "exception_type": type(e).__name__,
                "reproduced": False,
            }
            suspicions = localize_fault(error_text, file_path=file_path)
            return {
                "repro": repro,
                "localization": summarize_suspicions(suspicions),
            }
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict() if hasattr(repro, "to_dict") else repro,
            "localization": summarize_suspicions(suspicions),
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict() if hasattr(repro, "to_dict") else repro,
        "localization": summarize_suspicions(suspicions),
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

    if kind == "runtime_file_missing":
        if context and getattr(context, "file_path", "") and str(getattr(context, "file_path")).endswith(".py"):
            if isinstance(code, str) and code.strip():
                py = verify_python(code)
                py["mode"] = kind
                py["reason"] = f"operational fix with python payload validation: {py.get('reason', '')}"
                return py
        return {
            "ok": True,
            "reason": "operational file fix for non-python target; skipped python syntax verification",
            "mode": kind,
        }

    if kind in {"shell_command", "shell_runtime", "shell_command_missing", "shell_permission_denied", "shell_missing_path"}:
        if isinstance(code, str) and code.strip():
            py = verify_python(code)
            py["mode"] = kind
            py["reason"] = f"operational fix with python payload validation: {py.get('reason', '')}"
            return py
        return {
            "ok": True,
            "reason": "non-python operational fix; skipped python syntax verification",
            "mode": kind or "operational",
        }

    if isinstance(code, str) and code.strip():
        return verify_python(code)

    return {"ok": True, "reason": "no code payload"}


def _apply_candidate(candidate, file_path: str | None):
    c = _normalize_candidate(candidate)
    if not file_path:
        return {
            "applied": False,
            "reason": "no file_path provided",
            "backup_path": None,
        }

    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {
            "applied": False,
            "reason": f"candidate kind not auto-applicable: {kind or 'unknown'}",
            "backup_path": None,
        }

    if not isinstance(code, str) or not code.strip():
        return {
            "applied": False,
            "reason": "candidate_code empty",
            "backup_path": None,
        }

    target = file_path
    backup = make_backup(target)
    apply_text_replacement(target, code)

    verify_result = verify_python(code)
    if not verify_result.get("ok", False):
        restore_backup(target, backup)
        return {
            "applied": False,
            "reason": "post-apply verification failed; restored backup",
            "backup_path": str(backup),
            "verify": verify_result,
        }

    return {
        "applied": True,
        "reason": "patch applied and verified",
        "backup_path": str(backup),
        "verify": verify_result,
    }


def _execute_candidate(candidate, *, dry_run: bool = False, cwd: str | None = None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    metadata = c.get("metadata", {}) or {}
    patch = c.get("patch", None)

    if kind not in {"shell_command_missing", "shell_permission_denied", "shell_missing_path", "runtime_file_missing"}:
        return {
            "executed": False,
            "reason": f"candidate kind not executable: {kind or 'unknown'}",
            "results": [],
        }

    command_text = patch
    if not command_text:
        suggestions = metadata.get("suggestions", [])
        if kind == "shell_command_missing":
            command_text = " && ".join(suggestions[:3]) if suggestions else None
        elif kind == "shell_permission_denied":
            command_text = " && ".join(suggestions[:2]) if suggestions else patch
        elif kind in {"shell_missing_path", "runtime_file_missing"}:
            command_text = " && ".join([s for s in suggestions if s.startswith(("mkdir -p", "touch", "chmod +x"))])

    return execute_safe_suggestions(command_text, dry_run=dry_run, cwd=cwd)


def _fallback_pipeline(
    error_text: str,
    file_path: str | None = None,
    auto_apply: bool = False,
    exec_suggestions: bool = False,
    dry_run: bool = False,
    semantic: dict[str, Any] | None = None,
):
    context = build_context(error_text=error_text, file_path=file_path)
    if semantic is not None:
        try:
            setattr(context, "semantic", semantic)
        except Exception:
            pass

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

    normalized_candidates = _normalize_candidates(candidates)
    ranker = RankerAdapter()
    ranked = ranker.rank(normalized_candidates, context=context)
    best = ranked[0] if isinstance(ranked, list) and ranked else None

    verify_result = _verify_candidate(best, context=context)
    sandbox_result = run_in_sandbox(best, context)
    apply_result = None
    exec_result = None

    if auto_apply and best is not None:
        apply_result = _apply_candidate(best, file_path=file_path)

    if exec_suggestions and best is not None:
        exec_result = _execute_candidate(best, dry_run=dry_run)

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "routes": routes,
        "candidates": normalized_candidates,
        "best": _normalize_candidate(best) if best is not None else None,
        "verify": verify_result,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }

    EventStoreAdapter().append_event(payload)

    return {
        "result": _normalize_candidate(best) if best is not None else None,
        "semantic": semantic,
        "routes": routes,
        "verify": verify_result,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }


def run_autofix(
    error_text: str,
    file_path: str | None = None,
    auto_apply: bool = False,
    exec_suggestions: bool = False,
    dry_run: bool = False,
):
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    context = build_context(error_text=error_text, file_path=file_path)
    try:
        setattr(context, "semantic", semantic)
    except Exception:
        pass

    try:
        orchestrator = _build_orchestrator()
        result = orchestrator.run(context)
    except Exception:
        return _fallback_pipeline(
            error_text=error_text,
            file_path=file_path,
            auto_apply=auto_apply,
            exec_suggestions=exec_suggestions,
            dry_run=dry_run,
            semantic=semantic,
        )

    normalized_result = _normalize_candidate(result)
    verify_result = _verify_candidate(normalized_result, context=context)
    sandbox_result = run_in_sandbox(normalized_result, context)
    apply_result = None
    exec_result = None

    if auto_apply:
        apply_result = _apply_candidate(normalized_result, file_path=file_path)

    if exec_suggestions:
        exec_result = _execute_candidate(normalized_result, dry_run=dry_run)

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "result": normalized_result,
        "verify": verify_result,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }

    try:
        EventStoreAdapter().append_event(payload)
    except Exception:
        pass

    return {
        "result": normalized_result,
        "semantic": semantic,
        "verify": verify_result,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }
'''


def main() -> int:
    backup = TARGET.with_suffix(".py.bak")
    if TARGET.exists():
        backup.write_text(TARGET.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        print(f"[BACKUP] {backup}")

    TARGET.write_text(NEW_CONTENT, encoding="utf-8")
    print(f"[WRITE] {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
