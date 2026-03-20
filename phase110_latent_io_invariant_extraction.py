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
        for fp in reversed(traceback_files):
            if "/usr/lib/" in fp:
                continue
            return fp
        return getattr(context, "file_path", None)

    def _read_target_source(self, target_file: str | None, fallback_source: str) -> str:
        if not target_file:
            return fallback_source or ""
        try:
            return Path(target_file).read_text(encoding="utf-8")
        except Exception:
            return fallback_source or ""

    def _extract_latent_missing_path(self, source_code: str) -> str | None:
        src = source_code or ""

        patterns = [
            r'Path\("([^"]+)"\)\.read_text\(\)',
            r"Path\('([^']+)'\)\.read_text\(\)",
            r'open\("([^"]+)"\s*,\s*["\']r["\']\)',
            r"open\('([^']+)'\s*,\s*['\"]r['\"]\)",
        ]
        for pat in patterns:
            m = re.search(pat, src)
            if m:
                return m.group(1)
        return None

    def _guard_exists_variant(self, source_code: str, missing_path: str) -> str:
        src = source_code or ""
        exact1 = f'Path("{missing_path}").read_text()'
        repl1 = f'Path("{missing_path}").read_text() if Path("{missing_path}").exists() else ""'
        exact2 = f"Path('{missing_path}').read_text()"
        repl2 = f"Path('{missing_path}').read_text() if Path('{missing_path}').exists() else ''"

        if exact1 in src:
            return src.replace(exact1, repl1)
        if exact2 in src:
            return src.replace(exact2, repl2)

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
            if (not wrapped) and ("read_text()" in line or "open(" in line):
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
        traceback_files = self._extract_traceback_files(error_text)
        file_path = getattr(context, "file_path", None)
        fallback_source = getattr(context, "source_code", "") or ""

        target_file = self._choose_target_file(context, traceback_files)
        source_code = self._read_target_source(target_file, fallback_source)

        missing_path = self._extract_missing_path(error_text)
        if not missing_path:
            missing_path = self._extract_latent_missing_path(source_code)

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

        candidates = []

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

    "test_phase110_latent_io.py": r'''from __future__ import annotations

import json
import subprocess


def run(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def main():
    forced = run(["./termorganism", "demo/cross_file_dep.py", "--json", "--force-semantic"])
    payload = json.loads(forced["stdout"])

    best = payload.get("best_plan") or {}
    ev = best.get("evidence") or {}
    best_edit = ((best.get("edits") or [{}])[0])

    print(json.dumps({
        "forced_has_best_plan": bool(best),
        "forced_best_plan_id": best.get("plan_id"),
        "forced_strategy": ev.get("strategy"),
        "forced_provider": ev.get("provider"),
        "forced_caller": ev.get("caller"),
        "forced_best_kind": best_edit.get("kind"),
        "forced_has_candidate_code": bool((best_edit.get("candidate_code", "") or "").strip()),
        "forced_target_file": best_edit.get("file"),
        "forced_rank_tuple": best.get("rank_tuple"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
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
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
