#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/util/safe_exec.py": '''from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any


ALLOWED_BASE_COMMANDS = {
    "command",
    "which",
    "echo",
    "mkdir",
    "touch",
    "chmod",
}


def _is_safe_tokens(tokens: list[str]) -> tuple[bool, str]:
    if not tokens:
        return False, "empty command"

    base = tokens[0]

    if base not in ALLOWED_BASE_COMMANDS:
        return False, f"base command not allowed: {base}"

    if base == "command":
        if len(tokens) != 3 or tokens[1] != "-v":
            return False, "only 'command -v <name>' allowed"
        return True, "ok"

    if base == "which":
        if len(tokens) != 2:
            return False, "only 'which <name>' allowed"
        return True, "ok"

    if base == "echo":
        if tokens != ["echo", "$PATH"]:
            return False, "only 'echo $PATH' allowed"
        return True, "ok"

    if base == "mkdir":
        if len(tokens) < 3 or tokens[1] != "-p":
            return False, "only 'mkdir -p <path>' allowed"
        return True, "ok"

    if base == "touch":
        if len(tokens) != 2:
            return False, "only 'touch <path>' allowed"
        return True, "ok"

    if base == "chmod":
        if len(tokens) != 3 or tokens[1] != "+x":
            return False, "only 'chmod +x <path>' allowed"
        return True, "ok"

    return False, "unhandled command"


def _normalize_commands(command_text: str | None) -> list[str]:
    if not command_text or not isinstance(command_text, str):
        return []
    parts = [p.strip() for p in command_text.split("&&")]
    return [p for p in parts if p]


def execute_safe_suggestions(
    command_text: str | None,
    *,
    dry_run: bool = False,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    commands = _normalize_commands(command_text)
    results: list[dict[str, Any]] = []

    if not commands:
        return {
            "executed": False,
            "dry_run": dry_run,
            "results": [],
            "reason": "no commands to execute",
        }

    workdir = str(cwd) if cwd else None

    for cmd in commands:
        tokens = shlex.split(cmd)
        ok, reason = _is_safe_tokens(tokens)

        if not ok:
            results.append({
                "command": cmd,
                "allowed": False,
                "executed": False,
                "reason": reason,
            })
            continue

        if dry_run:
            results.append({
                "command": cmd,
                "allowed": True,
                "executed": False,
                "reason": "dry-run",
            })
            continue

        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        results.append({
            "command": cmd,
            "allowed": True,
            "executed": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })

    executed_any = any(r.get("executed", False) for r in results)
    all_allowed = all(r.get("allowed", False) for r in results) if results else False

    return {
        "executed": executed_any,
        "dry_run": dry_run,
        "all_allowed": all_allowed,
        "results": results,
    }
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
from core.memory import event_store, retrieval, stats
from core.util.patch_apply import make_backup, apply_text_replacement, restore_backup
from core.util.safe_exec import execute_safe_suggestions

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

    if kind not in {"shell_command_missing", "shell_permission_denied", "shell_missing_path"}:
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
            command_text = patch or " && ".join(suggestions[:2]) if suggestions else patch
        elif kind == "shell_missing_path":
            command_text = " && ".join([s for s in suggestions if s.startswith(("mkdir -p", "touch"))])

    return execute_safe_suggestions(command_text, dry_run=dry_run, cwd=cwd)


def _fallback_pipeline(
    error_text: str,
    file_path: str | None = None,
    auto_apply: bool = False,
    exec_suggestions: bool = False,
    dry_run: bool = False,
):
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
    context = build_context(error_text=error_text, file_path=file_path)

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
        "verify": verify_result,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }
''',

    "core/cli/autofix_cli.py": '''from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from core.autofix import run_autofix


def detect_error_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".py":
        proc = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return (proc.stderr or proc.stdout).strip()
        return ""

    return file_path.read_text(encoding="utf-8", errors="replace").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="termorganism-autofix",
        description="Run TermOrganism autofix pipeline on a target file.",
    )
    parser.add_argument(
        "target",
        help="Target file path. Python file or a text file containing an error log.",
    )
    parser.add_argument(
        "--error-text",
        help="Explicit error text. If omitted, CLI will try to derive it from target.",
        default=None,
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Apply eligible fixes to the target file after verification.",
    )
    parser.add_argument(
        "--exec",
        dest="exec_suggestions",
        action="store_true",
        help="Execute only whitelisted shell suggestions for executable shell candidates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --exec, only show what would run without executing it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON result.",
    )
    return parser


def summarize(result: dict) -> str:
    lines: list[str] = []

    candidate = result.get("result") or {}
    if not isinstance(candidate, dict):
        candidate = {"raw": str(candidate)}

    lines.append("TermOrganism Autofix Result")
    lines.append("=" * 32)
    lines.append(f"expert      : {candidate.get('expert', '-')}")
    lines.append(f"kind        : {candidate.get('kind', '-')}")
    lines.append(f"confidence  : {candidate.get('confidence', '-')}")
    lines.append(f"summary     : {candidate.get('summary', '-')}")
    lines.append(f"verify      : {result.get('verify', {}).get('ok', '-')}")
    lines.append(f"verify_note : {result.get('verify', {}).get('reason', '-')}")
    lines.append(f"sandbox     : {result.get('sandbox', {}).get('ok', '-')}")
    lines.append(f"routes      : {', '.join(result.get('routes', [])) if result.get('routes') else '-'}")

    apply_info = result.get("apply")
    if isinstance(apply_info, dict):
        lines.append(f"applied     : {apply_info.get('applied', False)}")
        lines.append(f"apply_note  : {apply_info.get('reason', '-')}")
        lines.append(f"backup_path : {apply_info.get('backup_path', '-')}")

    exec_info = result.get("exec")
    if isinstance(exec_info, dict):
        lines.append(f"exec_done   : {exec_info.get('executed', False)}")
        lines.append(f"exec_dryrun : {exec_info.get('dry_run', False)}")
        lines.append(f"exec_all_ok : {exec_info.get('all_allowed', '-')}")

    patch = candidate.get("patch")
    if isinstance(patch, str) and patch.strip():
        lines.append("")
        lines.append("patch:")
        lines.append(patch)

    metadata = candidate.get("metadata")
    if isinstance(metadata, dict) and metadata.get("suggestions"):
        lines.append("")
        lines.append("suggestions:")
        for s in metadata["suggestions"]:
            lines.append(f"  - {s}")

    return "\\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"HATA: hedef dosya bulunamadı: {target}", file=sys.stderr)
        return 2

    error_text = args.error_text
    if not error_text:
        error_text = detect_error_text(target)

    if not error_text:
        if args.json:
            print(json.dumps({
                "ok": True,
                "message": "No error detected. Target appears healthy.",
                "target": str(target),
                "changed": False,
            }, ensure_ascii=False, indent=2))
        else:
            print("Hata tespit edilmedi. Dosya zaten düzeltilmiş veya çalışır durumda.")
        return 0

    result = run_autofix(
        error_text=error_text,
        file_path=str(target),
        auto_apply=args.auto_apply,
        exec_suggestions=args.exec_suggestions,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(summarize(result))

    verify_ok = bool((result.get("verify") or {}).get("ok", False))
    return 0 if verify_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
''',

    "test_safe_exec.py": '''#!/usr/bin/env python3
from core.util.safe_exec import execute_safe_suggestions

cases = [
    ("mkdir -p demo_exec && touch demo_exec/sample.txt", True),
    ("chmod +x demo_exec/sample.txt", True),
    ("echo $PATH", True),
    ("sudo apt install bat", False),
    ("rm -rf demo_exec", False),
]

for cmd, should_be_allowed in cases:
    out = execute_safe_suggestions(cmd, dry_run=True)
    print("=" * 72)
    print(cmd)
    print(out)
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
