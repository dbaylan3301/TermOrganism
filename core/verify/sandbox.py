from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from core.verify.python_verify import verify_python
from core.verify.behavioral_verify import verify_python_runtime
from core.repro.project_workspace import build_temp_workspace


@dataclass
class SandboxResult:
    ok: bool
    reason: str
    candidate: Any = None
    temp_path: str = ""
    workspace_root: str = ""
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

    tmp, layout = build_temp_workspace(file_path)
    try:
        temp_target = Path(layout.target_dst)
        temp_target.write_text(code, encoding="utf-8")

        static_verify = verify_python(code)
        behavioral_verify = verify_python_runtime(temp_target).to_dict()

        ok = bool(static_verify.get("ok", False)) and bool(behavioral_verify.get("ok", False))
        reason = "sandbox static+runtime verification passed" if ok else "sandbox verification failed"

        result = SandboxResult(
            ok=ok,
            reason=reason,
            candidate=cand,
            temp_path=str(temp_target),
            workspace_root=layout.workspace_root,
            static_verify=static_verify,
            behavioral_verify=behavioral_verify,
        )
        return result.to_dict()
    finally:
        tmp.cleanup()
