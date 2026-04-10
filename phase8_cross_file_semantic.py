from __future__ import annotations
#!/usr/bin/env python3

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
            r"cannot access ['\\"]([^'\\"]+)['\\"]: No such file or directory",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "", flags=re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _candidate_target_files(self, context) -> list[str]:
        out: list[str] = []
        base = getattr(context, "file_path", None)
        if base:
            out.append(str(base))

        semantic = getattr(context, "semantic", None) or {}
        loc = (semantic.get("localization") or {}).get("items") or []
        for item in loc:
            if item.get("reason") == "import-neighbor candidate module":
                fp = item.get("file_path")
                if fp and fp not in out:
                    out.append(fp)
        return out

    def _make_candidates_for_target(self, *, target_file: str, missing_path: str, source_code: str) -> list[dict]:
        target = Path(missing_path)
        parent = str(target.parent) if str(target.parent) not in ("", ".") else ""

        shell_steps = []
        if parent:
            shell_steps.append(f"mkdir -p {parent}")
        shell_steps.append(f"touch {missing_path}")

        candidates = []

        candidates.append({
            "expert": self.name,
            "kind": "runtime_file_missing",
            "confidence": 0.70,
            "summary": f"Create missing runtime path: {missing_path}",
            "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
            "candidate_code": "",
            "file_path_hint": target_file,
            "target_file": target_file,
            "missing_path": missing_path,
            "hypothesis": "missing file is sufficient; caller can proceed once path exists",
            "semantic_claim": "creates missing path and file without changing source behavior",
            "affected_scope": [target_file],
            "metadata": {
                "strategy": "touch_only",
                "missing_path": missing_path,
                "parent_dir": parent,
                "shell_steps": shell_steps,
                "rationale": "operational remediation by creating the missing file path",
            },
        })

        if source_code and "read_text()" in source_code and ".exists()" not in source_code:
            guarded = source_code.replace(
                f'Path("{missing_path}").read_text()',
                f'Path("{missing_path}").read_text() if Path("{missing_path}").exists() else ""'
            )
            candidates.append({
                "expert": self.name,
                "kind": "runtime_file_missing",
                "confidence": 0.82,
                "summary": f"Guard missing file read with exists() fallback: {missing_path}",
                "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
                "candidate_code": guarded,
                "file_path_hint": target_file,
                "target_file": target_file,
                "missing_path": missing_path,
                "hypothesis": "failure comes from unguarded file read; add existence check",
                "semantic_claim": "prevents crash by guarding file read and returning empty fallback",
                "affected_scope": [target_file],
                "metadata": {
                    "strategy": "guard_exists",
                    "missing_path": missing_path,
                    "parent_dir": parent,
                    "shell_steps": shell_steps,
                    "rationale": "guarded file read with exists() fallback",
                },
            })

            wrapped = source_code.replace(
                f'print(Path("{missing_path}").read_text())',
                f'try:\\n    print(Path("{missing_path}").read_text())\\nexcept FileNotFoundError:\\n    print("")'
            )
            if wrapped != source_code:
                candidates.append({
                    "expert": self.name,
                    "kind": "runtime_file_missing",
                    "confidence": 0.74,
                    "summary": f"Wrap file read in FileNotFoundError recovery: {missing_path}",
                    "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
                    "candidate_code": wrapped,
                    "file_path_hint": target_file,
                    "target_file": target_file,
                    "missing_path": missing_path,
                    "hypothesis": "failure should be handled at runtime boundary instead of direct guard rewrite",
                    "semantic_claim": "prevents crash by catching FileNotFoundError and returning safe empty output",
                    "affected_scope": [target_file],
                    "metadata": {
                        "strategy": "try_except_recovery",
                        "missing_path": missing_path,
                        "parent_dir": parent,
                        "shell_steps": shell_steps,
                        "rationale": "runtime recovery through explicit exception handling",
                    },
                })

        return candidates

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""
        missing_path = self._extract_missing_path(error_text)

        if not missing_path:
            file_path = getattr(context, "file_path", None)
            return [{
                "expert": self.name,
                "kind": "runtime_file_missing",
                "confidence": 0.30,
                "summary": "Missing file suspected but path could not be extracted",
                "patch": None,
                "candidate_code": "",
                "file_path_hint": file_path,
                "target_file": file_path,
                "metadata": {},
                "affected_scope": [file_path] if file_path else [],
            }]

        candidates: list[dict] = []
        for target_file in self._candidate_target_files(context):
            source_code = ""
            try:
                p = Path(target_file)
                if p.exists() and p.suffix == ".py":
                    source_code = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                source_code = ""

            candidates.extend(
                self._make_candidates_for_target(
                    target_file=target_file,
                    missing_path=missing_path,
                    source_code=source_code,
                )
            )

        return candidates
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


def run_python_replay(file_path: str | Path, candidate_code: str | None = None, target_file: str | None = None) -> ReplayTestResult:
    base_file = target_file or file_path
    tmp, layout = build_temp_workspace(base_file)
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

    "test_phase8_cross_file.py": '''#!/usr/bin/env python3
from pathlib import Path
from core.autofix import run_autofix
import json

demo = Path("demo")
demo.mkdir(exist_ok=True)

(demo / "cross_file_dep.py").write_text(
    'from helper_mod import read_log\\n\\nprint(read_log())\\n',
    encoding="utf-8",
)
(demo / "helper_mod.py").write_text(
    'from pathlib import Path\\n\\ndef read_log():\\n    return Path("logs/app.log").read_text()\\n',
    encoding="utf-8",
)

error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

result = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "best_target_file": (result.get("result") or {}).get("target_file"),
    "best_scope": (result.get("result") or {}).get("affected_scope"),
    "candidate_count": result.get("candidate_count"),
    "candidate_targets": [
        {
            "summary": c.get("summary"),
            "target_file": c.get("target_file"),
            "scope": c.get("affected_scope"),
            "strategy": (c.get("metadata") or {}).get("strategy"),
        }
        for c in result.get("candidates", [])
    ],
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
