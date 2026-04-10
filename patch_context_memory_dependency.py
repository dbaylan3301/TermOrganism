from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/engine/context_builder.py": '''from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepairContext:
    error_text: str
    file_path: str | None = None
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""
    source_code: str = ""
    filename: str | None = None
    error_type: str = ""


def _infer_error_type(error_text: str) -> str:
    text = (error_text or "").lower()

    if "syntaxerror" in text:
        return "SyntaxError"
    if "indentationerror" in text:
        return "IndentationError"
    if "modulenotfounderror" in text:
        return "ModuleNotFoundError"
    if "filenotfounderror" in text:
        return "FileNotFoundError"
    if "permission denied" in text:
        return "PermissionError"
    if "command not found" in text:
        return "CommandNotFound"
    return ""


def _read_source(file_path: str | None) -> tuple[str, str | None]:
    if not file_path:
        return "", None

    p = Path(file_path)
    filename = p.name

    try:
        return p.read_text(encoding="utf-8", errors="replace"), filename
    except Exception:
        return "", filename


def build_context(
    error_text: str,
    file_path: str | None = None,
    stdout: str = "",
    stderr: str = "",
    traceback: str = "",
) -> RepairContext:
    source_code, filename = _read_source(file_path)

    return RepairContext(
        error_text=error_text,
        file_path=file_path,
        stdout=stdout,
        stderr=stderr,
        traceback=traceback,
        source_code=source_code,
        filename=filename,
        error_type=_infer_error_type(error_text),
    )
''',

    "core/memory/event_store.py": '''from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVENTS_PATH = Path("memory/TermOrganism/repair_events.jsonl")


def _ensure_path() -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not EVENTS_PATH.exists():
        EVENTS_PATH.touch()


def append_event(payload: dict[str, Any]) -> None:
    _ensure_path()
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\\n")


def store_event(payload: dict[str, Any]) -> None:
    append_event(payload)


def write_event(payload: dict[str, Any]) -> None:
    append_event(payload)


def read_events(limit: int | None = None) -> list[dict[str, Any]]:
    _ensure_path()
    lines = EVENTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    if limit is not None:
        lines = lines[-limit:]

    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"_raw": line, "_parse_error": True})
    return out
''',

    "core/experts/dependency.py": '''from __future__ import annotations

import re


class DependencyExpert:
    name = "dependency"

    def _extract_missing_module(self, error_text: str) -> str | None:
        patterns = [
            r"No module named ['\\"]([^'\\"]+)['\\"]",
            r"ModuleNotFoundError: No module named ['\\"]([^'\\"]+)['\\"]",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "")
            if m:
                return m.group(1)
        return None

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""
        missing = self._extract_missing_module(error_text)

        if not missing:
            return [{
                "expert": self.name,
                "confidence": 0.25,
                "summary": "Dependency issue suspected but missing package name could not be extracted",
                "patch": None,
                "candidate_code": "",
            }]

        return [{
            "expert": self.name,
            "confidence": 0.78,
            "summary": f"Missing dependency detected: {missing}",
            "patch": f"pip install {missing}",
            "candidate_code": "",
            "package": missing,
        }]
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
