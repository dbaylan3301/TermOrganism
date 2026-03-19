from __future__ import annotations

import hashlib
import re


def normalize_stderr(stderr: str) -> str:
    stderr = stderr.strip()
    stderr = re.sub(r"File \".*?\"", 'File "<file>"', stderr)
    stderr = re.sub(r"line \d+", "line <n>", stderr)
    stderr = re.sub(r"0x[0-9a-fA-F]+", "0x<addr>", stderr)
    return stderr


def error_fingerprint(stderr: str, exception_type: str | None = None) -> str:
    base = f"{exception_type or ''}|{normalize_stderr(stderr)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
