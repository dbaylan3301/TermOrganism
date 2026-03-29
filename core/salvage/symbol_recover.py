from __future__ import annotations

import ast
import builtins
import keyword
import re
from typing import Any

COMMON_IMPORT_RULES = [
    ("Path(", "from pathlib import Path"),
    ("json.", "import json"),
    ("os.", "import os"),
    ("sys.", "import sys"),
    ("re.", "import re"),
    ("requests.", "import requests"),
    ("pd.", "import pandas as pd"),
    ("np.", "import numpy as np"),
]

CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
IMPORT_LINE_RE = re.compile(r"^\s*(?:from\s+.+?\s+import\s+.+|import\s+.+)$", re.M)

BUILTIN_NAMES = set(dir(builtins)) | set(keyword.kwlist) | {
    "print", "len", "range", "open", "super", "self", "cls",
    "int", "str", "float", "dict", "list", "set", "tuple",
    "True", "False", "None",
}

def _ast_symbol_picture(source: str) -> dict[str, set[str]] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    imported: set[str] = set()
    defs: set[str] = set()
    classes: set[str] = set()
    direct_calls: set[str] = set()
    attr_calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.Import):
            for n in node.names:
                imported.add((n.asname or n.name.split(".")[0]))
        elif isinstance(node, ast.ImportFrom):
            for n in node.names:
                imported.add(n.asname or n.name)
            if node.module:
                imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                direct_calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                attr_calls.add(node.func.attr)

    return {
        "imported": imported,
        "defs": defs,
        "classes": classes,
        "direct_calls": direct_calls,
        "attr_calls": attr_calls,
    }

def recover_symbols(source: str, deep: bool = False) -> tuple[str, list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    src = source

    existing_defs = set(DEF_RE.findall(src))
    existing_classes = set(CLASS_RE.findall(src))
    existing_import_lines = set(IMPORT_LINE_RE.findall(src))

    prepend_imports: list[str] = []
    for needle, stmt in COMMON_IMPORT_RULES:
        if needle in src and stmt not in src:
            prepend_imports.append(stmt)
            changes.append({
                "kind": "synthetic_import",
                "detail": stmt,
                "confidence": 0.88,
            })

    picture = _ast_symbol_picture(src)
    imported_names: set[str] = set()
    missing_funcs: list[str] = []
    missing_classes: list[str] = []

    if picture is not None:
        imported_names = picture["imported"]
        direct_calls = sorted(
            x for x in picture["direct_calls"]
            if x not in BUILTIN_NAMES
            and x not in picture["defs"]
            and x not in picture["classes"]
            and x not in imported_names
            and not x.startswith("_")
        )

        for call in direct_calls:
            if call[:1].isupper():
                if call not in missing_classes:
                    missing_classes.append(call)
            else:
                if call not in missing_funcs:
                    missing_funcs.append(call)
    else:
        calls = [c for c in CALL_RE.findall(src) if c not in BUILTIN_NAMES]
        for call in calls:
            if call in existing_defs or call in existing_classes:
                continue
            if call.startswith("_"):
                continue
            if call[:1].isupper():
                if call not in missing_classes:
                    missing_classes.append(call)
            else:
                if call not in missing_funcs:
                    missing_funcs.append(call)

    synthesized_blocks: list[str] = []

    for name in missing_classes[:8]:
        if name in imported_names:
            continue
        synthesized_blocks.append(
f"""class {name}:
    # synthesized by termorganism salvage
    def __init__(self, *args, **kwargs):
        pass
"""
        )
        changes.append({
            "kind": "synthesized_class",
            "name": name,
            "confidence": 0.58,
            "reason": "direct constructor-like call seen but class definition missing",
        })

    for name in missing_funcs[:12]:
        if name in imported_names:
            continue
        synthesized_blocks.append(
f"""def {name}(*args, **kwargs):
    # synthesized by termorganism salvage
    return None
"""
        )
        changes.append({
            "kind": "synthesized_function",
            "name": name,
            "confidence": 0.61,
            "reason": "direct function call seen but definition missing",
        })

    if "main(" in src and "def main(" not in src and "main" not in imported_names:
        synthesized_blocks.append(
"""def main(*args, **kwargs):
    # synthesized by termorganism salvage
    return None
"""
        )
        changes.append({
            "kind": "synthesized_function",
            "name": "main",
            "confidence": 0.72,
            "reason": "main() referenced but missing",
        })

    if "def main(" in src and '__name__ == "__main__"' not in src and "__name__ == '__main__'" not in src:
        src = src.rstrip() + '\n\nif __name__ == "__main__":\n    main()\n'
        changes.append({
            "kind": "main_guard_added",
            "confidence": 0.86,
            "reason": "main() exists but no entry guard found",
        })

    if prepend_imports:
        block = "\n".join(x for x in prepend_imports if x not in existing_import_lines)
        if block:
            src = block + "\n" + src

    if synthesized_blocks:
        src = src.rstrip() + "\n\n# ---- synthesized by termorganism salvage ----\n\n" + "\n".join(synthesized_blocks).rstrip() + "\n"

    if deep and "logging." in src and "import logging" not in src:
        src = "import logging\n" + src
        changes.append({
            "kind": "synthetic_import",
            "detail": "import logging",
            "confidence": 0.84,
        })

    return src, changes
