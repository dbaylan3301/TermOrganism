from __future__ import annotations

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
