from __future__ import annotations

import re
from typing import Any

BLOCK_RE = re.compile(
    r"^(?P<indent>\s*)(?P<head>(?:if|elif|else|for|while|def|class|try|except|finally|with)\b.*?)(?P<colon>:?)\s*$"
)

def recover_syntax(source: str, deep: bool = False) -> tuple[str, list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    src = source.replace("\r\n", "\n").replace("\t", "    ")
    lines = src.split("\n")

    fixed: list[str] = []
    for idx, line in enumerate(lines, 1):
        m = BLOCK_RE.match(line)
        if m and not m.group("colon"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                line = line.rstrip() + ":"
                changes.append({
                    "kind": "syntax_colon_added",
                    "line": idx,
                    "detail": stripped,
                    "confidence": 0.92,
                })
        fixed.append(line)

    out: list[str] = []
    n = len(fixed)
    for i, line in enumerate(fixed):
        out.append(line)
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.endswith(":"):
            continue

        cur_indent = len(line) - len(line.lstrip(" "))
        j = i + 1
        while j < n and fixed[j].strip() == "":
            j += 1

        if j >= n:
            out.append(" " * (cur_indent + 4) + "pass")
            changes.append({
                "kind": "synthetic_pass",
                "line": i + 1,
                "detail": "terminal block body synthesized",
                "confidence": 0.81,
            })
            continue

        next_line = fixed[j]
        next_indent = len(next_line) - len(next_line.lstrip(" "))
        if next_line.strip() and next_indent <= cur_indent:
            out.append(" " * (cur_indent + 4) + "pass")
            changes.append({
                "kind": "synthetic_pass",
                "line": i + 1,
                "detail": "empty block body synthesized",
                "confidence": 0.81,
            })

    recovered = "\n".join(out).rstrip() + "\n"
    if deep:
        recovered = re.sub(r"\n{3,}", "\n\n", recovered)

    return recovered, changes
