#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/experts/file_runtime.py": r'''from __future__ import annotations

import re
from pathlib import Path


class FileRuntimeExpert:
    name = "file_runtime"

    def _extract_missing_path(self, error_text: str) -> str | None:
        patterns = [
            r"No such file or directory: ['\"]([^'\"]+)['\"]",
            r"FileNotFoundError: \[Errno 2\] No such file or directory: ['\"]([^'\"]+)['\"]",
            r"cannot access ['\"]([^'\"]+)['\"]: No such file or directory",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "", flags=re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _extract_traceback_files(self, error_text: str) -> list[str]:
        files: list[str] = []
        for m in re.finditer(r'File "([^"]+)", line (\d+)', error_text or ""):
            fp = m.group(1)
            if fp and fp.endswith(".py"):
                files.append(fp)
        return files

    def _choose_target_file(self, context, traceback_files: list[str]) -> str | None:
        # traceback'te stdlib dışı en derin kullanıcı dosyasını hedefle
        for fp in reversed(traceback_files):
            if "/usr/lib/" in fp:
                continue
            return fp

        file_path = getattr(context, "file_path", None)
        return file_path

    def _read_target_source(self, target_file: str | None, fallback_source: str) -> str:
        if not target_file:
            return fallback_source or ""
        try:
            return Path(target_file).read_text(encoding="utf-8")
        except Exception:
            return fallback_source or ""

    def _guard_exists_variant(self, source_code: str, missing_path: str) -> str:
        src = source_code or ""
        exact = f'Path("{missing_path}").read_text()'
        repl = f'Path("{missing_path}").read_text() if Path("{missing_path}").exists() else ""'

        if exact in src:
            return src.replace(exact, repl)

        # generic fallback: first Path(...).read_text()
        patched = re.sub(
            r'Path\(([^)]+)\)\.read_text\(\)',
            r'Path(\1).read_text() if Path(\1).exists() else ""',
            src,
            count=1,
        )
        return patched

    def _try_except_variant(self, source_code: str) -> str:
        src = source_code or ""
        lines = src.splitlines()
        if not lines:
            return ""

        out: list[str] = []
        wrapped = False
        for line in lines:
            if (not wrapped) and "read_text()" in line:
                indent = len(line) - len(line.lstrip(" "))
                pad = " " * indent
                out.append(f"{pad}try:")
                out.append(f"{pad}    {line.lstrip()}")
                out.append(f"{pad}except FileNotFoundError:")
                out.append(f'{pad}    return ""' if "return " in line else f'{pad}    print("")')
                wrapped = True
            else:
                out.append(line)
        return "\n".join(out) + ("\n" if src.endswith("\n") else "")

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""
        missing_path = self._extract_missing_path(error_text)
        traceback_files = self._extract_traceback_files(error_text)
        file_path = getattr(context, "file_path", None)
        fallback_source = getattr(context, "source_code", "") or ""

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

        target_file = self._choose_target_file(context, traceback_files)
        source_code = self._read_target_source(target_file, fallback_source)

        target = Path(missing_path)
        parent = str(target.parent) if str(target.parent) not in ("", ".") else ""

        shell_steps = []
        if parent:
            shell_steps.append(f"mkdir -p {parent}")
        shell_steps.append(f"touch {missing_path}")

        candidates = []

        # 1) operational
        candidates.append({
            "expert": self.name,
            "kind": "runtime_file_missing",
            "confidence": 0.70,
            "summary": f"Create missing runtime path: {missing_path}",
            "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
            "candidate_code": "",
            "file_path_hint": target_file or file_path,
            "target_file": target_file or file_path,
            "missing_path": missing_path,
            "hypothesis": "missing file is sufficient; caller can proceed once path exists",
            "semantic_claim": "creates missing path and file without changing source behavior",
            "affected_scope": [target_file or file_path] if (target_file or file_path) else [],
            "metadata": {
                "strategy": "touch_only",
                "missing_path": missing_path,
                "parent_dir": parent,
                "shell_steps": shell_steps,
                "rationale": "operational remediation by creating the missing file path",
            },
            "blast_radius": 0.05,
        })

        if source_code.strip():
            guarded = self._guard_exists_variant(source_code, missing_path)
            if guarded and guarded != source_code:
                candidates.append({
                    "expert": self.name,
                    "kind": "runtime_file_missing",
                    "confidence": 0.82,
                    "summary": f"Guard missing file read with exists() fallback: {missing_path}",
                    "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
                    "candidate_code": guarded,
                    "file_path_hint": target_file or file_path,
                    "target_file": target_file or file_path,
                    "missing_path": missing_path,
                    "hypothesis": "failure comes from unguarded file read; add existence check",
                    "semantic_claim": "prevents crash by guarding file read and returning empty fallback",
                    "affected_scope": [target_file or file_path] if (target_file or file_path) else [],
                    "metadata": {
                        "strategy": "guard_exists",
                        "missing_path": missing_path,
                        "parent_dir": parent,
                        "shell_steps": shell_steps,
                        "rationale": "guarded file read with exists() fallback",
                    },
                    "blast_radius": 0.12,
                })

            wrapped = self._try_except_variant(source_code)
            if wrapped and wrapped != source_code:
                candidates.append({
                    "expert": self.name,
                    "kind": "runtime_file_missing",
                    "confidence": 0.74,
                    "summary": f"Wrap file read in FileNotFoundError recovery: {missing_path}",
                    "patch": "mkdir -p {0} && touch {1}".format(parent, missing_path) if parent else f"touch {missing_path}",
                    "candidate_code": wrapped,
                    "file_path_hint": target_file or file_path,
                    "target_file": target_file or file_path,
                    "missing_path": missing_path,
                    "hypothesis": "failure should be handled at runtime boundary instead of direct guard rewrite",
                    "semantic_claim": "prevents crash by catching FileNotFoundError and returning safe empty output",
                    "affected_scope": [target_file or file_path] if (target_file or file_path) else [],
                    "metadata": {
                        "strategy": "try_except_recovery",
                        "missing_path": missing_path,
                        "parent_dir": parent,
                        "shell_steps": shell_steps,
                        "rationale": "runtime recovery through explicit exception handling",
                    },
                    "blast_radius": 0.18,
                })

        return candidates
''',

    "test_phase107_provider_rebinding.py": r'''from __future__ import annotations

import json
from core.autofix import run_autofix

error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/usr/lib/python3.13/pathlib/_local.py", line 548, in read_text
    return PathBase.read_text(self, encoding, errors, newline)
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""

res = run_autofix(
    error_text=error_text,
    file_path="demo/cross_file_dep.py",
)

planner = res.get("planner") or {}
best = res.get("best_plan") or {}
best_edit = ((best.get("edits") or [{}])[0])

print(json.dumps({
    "candidate_count": planner.get("candidate_count"),
    "base_plan_count": planner.get("base_plan_count"),
    "multifile_plan_count": planner.get("multifile_plan_count"),
    "best_plan_id": best.get("plan_id"),
    "strategy": (best.get("evidence") or {}).get("strategy"),
    "best_kind": best_edit.get("kind"),
    "best_has_candidate_code": bool((best_edit.get("candidate_code", "") or "").strip()),
    "best_target_file": best_edit.get("file"),
    "top_8": [
        {
            "plan_id": p.get("plan_id"),
            "strategy": (p.get("evidence") or {}).get("strategy"),
            "kind": ((p.get("edits") or [{}])[0]).get("kind"),
            "has_candidate_code": bool((((p.get("edits") or [{}])[0]).get("candidate_code", "") or "").strip()),
            "target_file": ((p.get("edits") or [{}])[0]).get("file"),
            "rank_tuple": p.get("rank_tuple"),
        }
        for p in (planner.get("repair_plans") or [])[:8]
    ],
}, indent=2, ensure_ascii=False))
'''
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
