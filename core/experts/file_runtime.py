from __future__ import annotations

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
        is_python_source = bool(file_path and str(file_path).endswith(".py"))
        patched_code = source_code if is_python_source else ""
        rationale = "create missing file path before read attempt"

        if (
            is_python_source
            and source_code
            and "read_text()" in source_code
            and ".exists()" not in source_code
        ):
            patched_code = source_code.replace(
                f'Path("{missing_path}").read_text()',
                f'Path("{missing_path}").read_text() if Path("{missing_path}").exists() else ""'
            )
            rationale = "guarded file read with exists() fallback"

        patch_cmd = f"mkdir -p {parent} && touch {missing_path}" if parent else f"touch {missing_path}"

        return [{
            "expert": self.name,
            "kind": "runtime_file_missing",
            "confidence": 0.82,
            "summary": f"Missing runtime file detected: {missing_path}",
            "patch": patch_cmd,
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
