#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/verify/sandbox.py": '''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import shutil

from core.verify.python_verify import verify_python
from core.verify.behavioral_verify import verify_python_runtime


@dataclass
class SandboxResult:
    ok: bool
    reason: str
    candidate: Any = None
    temp_path: str = ""
    static_verify: dict[str, Any] | None = None
    behavioral_verify: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VerifierHub:
    def verify(self, candidate, context=None):
        return run_in_sandbox(candidate, context)


def _normalize_candidate(candidate: Any) -> dict[str, Any]:
    if isinstance(candidate, dict):
        return dict(candidate)
    return {"raw_candidate": str(candidate)}


def _copy_target_to_temp(file_path: str, tmpdir: str) -> tuple[str, str]:
    src = Path(file_path).resolve()
    dst_dir = Path(tmpdir) / "workspace"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return str(src), str(dst)


def _write_candidate_code(temp_file_path: str, code: str) -> None:
    Path(temp_file_path).write_text(code, encoding="utf-8")


def run_in_sandbox(candidate, context=None):
    cand = _normalize_candidate(candidate)
    file_path = getattr(context, "file_path", None) if context is not None else None
    kind = cand.get("kind", "") or ""
    code = cand.get("candidate_code", "") or ""

    if not file_path:
        return {
            "ok": True,
            "reason": "sandbox skipped: no file_path",
            "candidate": cand,
        }

    if not str(file_path).endswith(".py"):
        return {
            "ok": True,
            "reason": "sandbox skipped: non-python target",
            "candidate": cand,
        }

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {
            "ok": True,
            "reason": f"sandbox skipped: unsupported candidate kind {kind or 'unknown'}",
            "candidate": cand,
        }

    if not isinstance(code, str) or not code.strip():
        return {
            "ok": True,
            "reason": "sandbox skipped: no candidate_code payload",
            "candidate": cand,
        }

    with TemporaryDirectory(prefix="termorganism_sandbox_") as tmpdir:
        _, temp_target = _copy_target_to_temp(str(file_path), tmpdir)
        _write_candidate_code(temp_target, code)

        static_verify = verify_python(code)
        behavioral_verify = verify_python_runtime(temp_target).to_dict()

        ok = bool(static_verify.get("ok", False)) and bool(behavioral_verify.get("ok", False))
        reason = "sandbox static+runtime verification passed" if ok else "sandbox verification failed"

        result = SandboxResult(
            ok=ok,
            reason=reason,
            candidate=cand,
            temp_path=temp_target,
            static_verify=static_verify,
            behavioral_verify=behavioral_verify,
        )
        return result.to_dict()
''',

    "core/autofix.py": r'''from __future__ import annotations

from typing import Any
import ast
import re

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.engine.router import PolicyRouter
from core.verify.sandbox import VerifierHub, run_in_sandbox
from core.verify.python_verify import verify_python
from core.verify.behavioral_verify import verify_python_runtime, verify_repro_delta
from core.memory import event_store, retrieval, stats
from core.util.patch_apply import make_backup, apply_text_replacement, restore_backup
from core.util.safe_exec import execute_safe_suggestions
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions

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


class RankerAdapter:
    def _score(self, candidate):
        if isinstance(candidate, dict):
            base = float(candidate.get("confidence", 0.0) or 0.0)
            repro_fix = float(candidate.get("repro_fix_score", 0.0) or 0.0)
            regression = float(candidate.get("regression_score", 0.0) or 0.0)
            prior = float(candidate.get("historical_success_prior", 0.0) or 0.0)
            blast_radius = float(candidate.get("blast_radius", 0.0) or 0.0)
            sandbox_bonus = 0.10 if ((candidate.get("sandbox") or {}).get("ok") is True) else 0.0
            return base + repro_fix + regression + prior + sandbox_bonus - blast_radius
        return getattr(candidate, "confidence", 0.0)

    def rank(self, candidates, context=None):
        if not isinstance(candidates, list):
            return candidates
        return sorted(candidates, key=self._score, reverse=True)


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


def _build_orchestrator() -> Orchestrator:
    return Orchestrator(
        router=PolicyRouter(),
        experts=ExpertAdapter(),
        verifier=VerifierHub(),
        ranker=RankerAdapter(),
        store=EventStoreAdapter(),
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
        c.setdefault("kind", "")
        c.setdefault("confidence", 0.0)
        c.setdefault("candidate_code", "")
        c.setdefault("metadata", {})
        c.setdefault("repro_fix_score", 0.0)
        c.setdefault("regression_score", 0.0)
        c.setdefault("historical_success_prior", 0.0)
        c.setdefault("blast_radius", 0.0)
        c.setdefault("hypothesis", "")
        c.setdefault("semantic_claim", "")
        c.setdefault("affected_scope", [])
        patch = c.get("patch")
        if c["kind"] == "" and isinstance(patch, str) and patch.startswith("pip install "):
            c["kind"] = "dependency_install"
        elif c["kind"] == "" and c.get("expert") == "file_runtime":
            c["kind"] = "runtime_file_missing"
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
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
        }

    text = str(candidate)
    if "RepairCandidate(" in text:
        return {
            "expert": _extract_field(text, "expert_name") or "python_syntax",
            "kind": _extract_field(text, "kind") or "python_patch",
            "confidence": _extract_field(text, "expert_score") or 0.0,
            "summary": _extract_field(text, "rationale") or text,
            "patch": _extract_field(text, "patch_unified_diff"),
            "candidate_code": _extract_field(text, "patched_code") or "",
            "raw_candidate": text,
            "metadata": {},
            "router_score": _extract_field(text, "router_score") or 0.0,
            "expert_score": _extract_field(text, "expert_score") or 0.0,
            "memory_prior": _extract_field(text, "memory_prior") or 0.0,
            "patch_safety_score": _extract_field(text, "patch_safety_score") or 0.0,
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
        }

    return {
        "expert": "unknown",
        "kind": "unknown",
        "confidence": 0.0,
        "summary": text,
        "patch": None,
        "candidate_code": "",
        "raw_candidate": text,
        "metadata": {},
        "repro_fix_score": 0.0,
        "regression_score": 0.0,
        "historical_success_prior": 0.0,
        "blast_radius": 0.0,
        "hypothesis": "",
        "semantic_claim": "",
        "affected_scope": [],
    }


def _normalize_candidates(candidates):
    if not isinstance(candidates, list):
        return candidates
    return [_normalize_candidate(c) for c in candidates]


def _build_semantic_prelude(error_text: str, file_path: str | None):
    if file_path and str(file_path).endswith(".py"):
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict(),
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
        return {"ok": True, "reason": "dependency install suggestion accepted as non-python command candidate", "mode": "dependency_install"}

    if kind == "runtime_file_missing":
        if context and getattr(context, "file_path", "") and str(getattr(context, "file_path")).endswith(".py"):
            if isinstance(code, str) and code.strip():
                py = verify_python(code)
                py["mode"] = kind
                py["reason"] = f"operational fix with python payload validation: {py.get('reason', '')}"
                return py
        return {"ok": True, "reason": "operational file fix for non-python target; skipped python syntax verification", "mode": kind}

    if kind in {"shell_command", "shell_runtime", "shell_command_missing", "shell_permission_denied", "shell_missing_path"}:
        return {"ok": True, "reason": "non-python operational fix; skipped python syntax verification", "mode": kind or "operational"}

    if isinstance(code, str) and code.strip():
        return verify_python(code)

    return {"ok": True, "reason": "no code payload"}


def _apply_candidate(candidate, file_path: str | None):
    c = _normalize_candidate(candidate)
    if not file_path:
        return {"applied": False, "reason": "no file_path provided", "backup_path": None}

    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"applied": False, "reason": f"candidate kind not auto-applicable: {kind or 'unknown'}", "backup_path": None}

    if not isinstance(code, str) or not code.strip():
        return {"applied": False, "reason": "candidate_code empty", "backup_path": None}

    backup = make_backup(file_path)
    apply_text_replacement(file_path, code)

    verify_result = verify_python(code)
    if not verify_result.get("ok", False):
        restore_backup(file_path, backup)
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
        return {"executed": False, "reason": f"candidate kind not executable: {kind or 'unknown'}", "results": []}

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


def _behavioral_verify_for_candidate(candidate, file_path: str | None, semantic_before: dict[str, Any] | None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""

    if not file_path or not str(file_path).endswith(".py"):
        return {"ok": True, "mode": "behavioral_skip", "reason": "non-python target; behavioral runtime verify skipped"}

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"ok": True, "mode": "behavioral_skip", "reason": f"candidate kind not behaviorally executed: {kind or 'unknown'}"}

    code = c.get("candidate_code", "") or ""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "mode": "behavioral_skip", "reason": "candidate_code empty"}

    before_stderr = (((semantic_before or {}).get("repro") or {}).get("stderr", "")) if isinstance(semantic_before, dict) else ""

    backup = make_backup(file_path)
    try:
        apply_text_replacement(file_path, code)
        runtime = verify_python_runtime(file_path).to_dict()
        delta = verify_repro_delta(before_stderr, runtime.get("stderr", "")).to_dict()

        ok = bool(runtime.get("ok", False)) or bool(delta.get("ok", False))
        return {
            "ok": ok,
            "mode": "behavioral_verify",
            "reason": "behavioral verification completed",
            "runtime": runtime,
            "delta": delta,
            "repro_fix_score": 0.75 if delta.get("ok", False) else 0.0,
            "regression_score": 0.65 if runtime.get("ok", False) else 0.0,
        }
    finally:
        restore_backup(file_path, backup)


def _evaluate_candidates(candidates, *, file_path: str | None, semantic: dict[str, Any] | None):
    normalized = _normalize_candidates(candidates)
    enriched = []

    for cand in normalized:
        bv = _behavioral_verify_for_candidate(cand, file_path, semantic)
        cand2 = dict(cand)
        cand2["behavioral_verify"] = bv
        cand2["repro_fix_score"] = float(bv.get("repro_fix_score", 0.0) or 0.0)
        cand2["regression_score"] = float(bv.get("regression_score", 0.0) or 0.0)
        cand2["historical_success_prior"] = float(retrieval.candidate_history_prior(cand2) or 0.0)

        strategy = ((cand2.get("metadata") or {}).get("strategy", "")) if isinstance(cand2.get("metadata"), dict) else ""
        if strategy == "touch_only":
            cand2["blast_radius"] = 0.05
        elif strategy == "guard_exists":
            cand2["blast_radius"] = 0.12
        elif strategy == "try_except_recovery":
            cand2["blast_radius"] = 0.18
        else:
            cand2["blast_radius"] = float(cand2.get("blast_radius", 0.0) or 0.0)

        # real temp sandbox
        sandbox_context = build_context(error_text="", file_path=file_path)
        cand2["sandbox"] = run_in_sandbox(cand2, sandbox_context)

        enriched.append(cand2)

    ranked = RankerAdapter().rank(enriched)
    best = ranked[0] if ranked else None
    return enriched, best


def _fallback_pipeline(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False, semantic: dict[str, Any] | None = None):
    context = build_context(error_text=error_text, file_path=file_path)
    try:
        setattr(context, "semantic", semantic)
    except Exception:
        pass

    routes = PolicyRouter().route(context)

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

    enriched, best = _evaluate_candidates(candidates, file_path=file_path, semantic=semantic)

    verify_result = _verify_candidate(best, context=context)
    sandbox_result = (best or {}).get("sandbox") if isinstance(best, dict) else None
    apply_result = _apply_candidate(best, file_path=file_path) if auto_apply and best is not None else None
    exec_result = _execute_candidate(best, dry_run=dry_run) if exec_suggestions and best is not None else None
    behavioral_verify = (best or {}).get("behavioral_verify") if isinstance(best, dict) else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "routes": routes,
        "candidates": enriched,
        "best": _normalize_candidate(best) if best is not None else None,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
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
        "behavioral_verify": behavioral_verify,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False):
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    context = build_context(error_text=error_text, file_path=file_path)
    try:
        setattr(context, "semantic", semantic)
    except Exception:
        pass

    try:
        result = _build_orchestrator().run(context)
    except Exception:
        return _fallback_pipeline(
            error_text=error_text,
            file_path=file_path,
            auto_apply=auto_apply,
            exec_suggestions=exec_suggestions,
            dry_run=dry_run,
            semantic=semantic,
        )

    candidates = result if isinstance(result, list) else [result]
    enriched, best = _evaluate_candidates(candidates, file_path=file_path, semantic=semantic)

    verify_result = _verify_candidate(best, context=context)
    behavioral_verify = (best or {}).get("behavioral_verify") if isinstance(best, dict) else None
    sandbox_result = (best or {}).get("sandbox") if isinstance(best, dict) else None
    apply_result = _apply_candidate(best, file_path=file_path) if auto_apply and best is not None else None
    exec_result = _execute_candidate(best, dry_run=dry_run) if exec_suggestions and best is not None else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "result": _normalize_candidate(best) if best is not None else None,
        "candidates": enriched,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }
    EventStoreAdapter().append_event(payload)

    return {
        "result": _normalize_candidate(best) if best is not None else None,
        "semantic": semantic,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }
''',

    "test_real_sandbox.py": '''#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\\n  File \\"demo/broken_runtime.py\\", line 3, in <module>\\n    print(Path(\\"logs/app.log\\").read_text())\\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "sandbox": result.get("sandbox"),
    "candidate_sandboxes": [
        {
            "strategy": ((c.get("metadata") or {}).get("strategy")),
            "sandbox_ok": ((c.get("sandbox") or {}).get("ok")),
            "sandbox_reason": ((c.get("sandbox") or {}).get("reason")),
        }
        for c in result.get("candidates", [])
    ]
}, ensure_ascii=False, indent=2))
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


def main() -> int:
    for rel_path, content in PATCHES.items():
        backup_and_write(rel_path, content)
    print("\\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
