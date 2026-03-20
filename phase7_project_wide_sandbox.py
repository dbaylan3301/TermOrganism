#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/repro/project_workspace.py": '''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import shutil


@dataclass
class WorkspaceLayout:
    root: str
    workspace_root: str
    target_src: str
    target_dst: str
    project_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _guess_project_root(target: Path) -> Path:
    cur = target.resolve().parent
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}

    for base in [cur, *cur.parents]:
        if any((base / m).exists() for m in markers):
            return base

    return target.resolve().parent


def _copy_tree_filtered(src_root: Path, dst_root: Path) -> None:
    ignore_dirs = {
        "__pycache__", ".git", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", ".venv", "venv", "node_modules"
    }
    allow_suffixes = {".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".md"}

    for path in src_root.rglob("*"):
        rel = path.relative_to(src_root)

        if any(part in ignore_dirs for part in rel.parts):
            continue

        dst = dst_root / rel

        if path.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        if path.suffix.lower() in allow_suffixes or path.name in {"README", "LICENSE"}:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)


def build_temp_workspace(file_path: str | Path):
    target = Path(file_path).resolve()
    project_root = _guess_project_root(target)

    tmp = TemporaryDirectory(prefix="termorganism_project_ws_")
    workspace_root = Path(tmp.name) / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    _copy_tree_filtered(project_root, workspace_root)

    target_dst = workspace_root / target.relative_to(project_root)

    layout = WorkspaceLayout(
        root=tmp.name,
        workspace_root=str(workspace_root),
        target_src=str(target),
        target_dst=str(target_dst),
        project_root=str(project_root),
    )
    return tmp, layout
''',

    "core/semantic/fault_localizer.py": '''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re


@dataclass
class Suspicion:
    file_path: str
    line_no: int | None
    symbol: str | None
    reason: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TRACE_FILE_RE = re.compile(r'File "([^"]+)", line ([0-9]+)')
IMPORT_RE = re.compile(r'^(?:from\\s+([a-zA-Z0-9_\\.]+)\\s+import|import\\s+([a-zA-Z0-9_\\.]+))', re.MULTILINE)


def _collect_trace_suspicions(error_text: str) -> list[Suspicion]:
    out: list[Suspicion] = []
    for m in TRACE_FILE_RE.finditer(error_text or ""):
        out.append(
            Suspicion(
                file_path=m.group(1),
                line_no=int(m.group(2)),
                symbol=None,
                reason="traceback-localized frame",
                score=0.88,
            )
        )
    return out


def _collect_signature_suspicions(error_text: str, file_path: str | None) -> list[Suspicion]:
    text = error_text or ""
    path = file_path or "<unknown>"
    out: list[Suspicion] = []

    lowered = text.lower()

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        out.append(Suspicion(path, 1, None, "dependency/import failure at module import boundary", 0.84))

    if "filenotfounderror" in lowered or "no such file or directory" in lowered:
        out.append(Suspicion(path, None, None, "runtime path/file access failure", 0.82))

    if "syntaxerror" in lowered or "indentationerror" in lowered:
        out.append(Suspicion(path, None, None, "syntax failure in target module", 0.86))

    if "command not found" in lowered:
        out.append(Suspicion(path, None, None, "shell executable resolution failure", 0.76))

    if "permission denied" in lowered:
        out.append(Suspicion(path, None, None, "permission boundary failure", 0.73))

    if not out:
        out.append(Suspicion(path, None, None, "generic localized failure", 0.50))

    return out


def _collect_import_neighbors(file_path: str | None) -> list[Suspicion]:
    if not file_path:
        return []

    p = Path(file_path)
    if not p.exists() or p.suffix != ".py":
        return []

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    out: list[Suspicion] = []
    seen: set[str] = set()

    for m in IMPORT_RE.finditer(text):
        mod = m.group(1) or m.group(2) or ""
        base = mod.split(".")[0].strip()
        if not base or base in seen:
            continue
        seen.add(base)

        neighbor = p.parent / f"{base}.py"
        if neighbor.exists():
            out.append(
                Suspicion(
                    file_path=str(neighbor.resolve()),
                    line_no=None,
                    symbol=base,
                    reason="import-neighbor candidate module",
                    score=0.42,
                )
            )

    return out


def localize_fault(error_text: str, file_path: str | None = None) -> list[Suspicion]:
    items: list[Suspicion] = []
    items.extend(_collect_trace_suspicions(error_text))
    items.extend(_collect_signature_suspicions(error_text, file_path))
    items.extend(_collect_import_neighbors(file_path))

    # deduplicate, keep max score
    best: dict[tuple[str, int | None, str | None, str], Suspicion] = {}
    for item in items:
        key = (item.file_path, item.line_no, item.symbol, item.reason)
        if key not in best or item.score > best[key].score:
            best[key] = item

    return sorted(best.values(), key=lambda x: x.score, reverse=True)


def summarize_suspicions(items: list[Suspicion]) -> dict[str, Any]:
    arr = [x.to_dict() if hasattr(x, "to_dict") else x for x in items]
    return {
        "count": len(arr),
        "top": arr[0] if arr else None,
        "items": arr,
    }
''',

    "core/verify/sandbox.py": '''from __future__ import annotations

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
''',

    "core/testsynth/replay_test.py": '''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess
import sys

from core.repro.project_workspace import build_temp_workspace


@dataclass
class ReplayTestResult:
    ok: bool
    mode: str
    reason: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    workspace_root: str = ""
    temp_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_python_replay(file_path: str | Path, candidate_code: str | None = None) -> ReplayTestResult:
    tmp, layout = build_temp_workspace(file_path)
    try:
        temp_target = Path(layout.target_dst)
        if candidate_code is not None and candidate_code.strip():
            temp_target.write_text(candidate_code, encoding="utf-8")

        rel_target = temp_target.relative_to(Path(layout.workspace_root))

        proc = subprocess.run(
            [sys.executable, str(rel_target)],
            cwd=str(layout.workspace_root),
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        return ReplayTestResult(
            ok=ok,
            mode="python_replay",
            reason="replay execution passed" if ok else "replay execution failed",
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            workspace_root=layout.workspace_root,
            temp_target=str(temp_target),
        )
    finally:
        tmp.cleanup()
''',

    "test_phase7_project_wide.py": '''#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\\n  File \\"demo/broken_runtime.py\\", line 3, in <module>\\n    print(Path(\\"logs/app.log\\").read_text())\\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "top_localization": ((result.get("semantic") or {}).get("localization") or {}).get("top"),
    "import_neighbors": [
        x for x in (((result.get("semantic") or {}).get("localization") or {}).get("items") or [])
        if x.get("reason") == "import-neighbor candidate module"
    ],
    "sandbox": result.get("sandbox"),
    "synthesized_tests": result.get("synthesized_tests"),
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
