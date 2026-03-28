from __future__ import annotations

import ast
import re
from dataclasses import dataclass, asdict
from typing import Any

CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.M)
IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z_][A-Za-z0-9_\.]+))", re.M)

@dataclass
class StructureScan:
    line_count: int
    imports: list[str]
    defs: list[str]
    classes: list[str]
    calls: list[str]
    has_main_guard: bool
    syntax_error: str | None
    entrypoint_candidates: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _unique(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def scan_structure(source: str) -> StructureScan:
    line_count = len(source.splitlines())
    imports = _unique([a or b for a, b in IMPORT_RE.findall(source)])
    defs = _unique(DEF_RE.findall(source))
    classes = _unique(CLASS_RE.findall(source))
    calls = _unique(CALL_RE.findall(source))
    has_main_guard = '__name__ == "__main__"' in source or "__name__ == '__main__'" in source
    entrypoint_candidates = [x for x in defs if x in {"main", "run", "start", "cli"}]

    syntax_error = None
    try:
        tree = ast.parse(source)
        defs_ast: list[str] = []
        classes_ast: list[str] = []
        calls_ast: list[str] = []
        imports_ast: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defs_ast.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                defs_ast.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes_ast.append(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls_ast.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls_ast.append(node.func.attr)
            elif isinstance(node, ast.Import):
                for n in node.names:
                    imports_ast.append(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports_ast.append(node.module.split(".")[0])

        defs = _unique(defs_ast) or defs
        classes = _unique(classes_ast) or classes
        calls = _unique(calls_ast) or calls
        imports = _unique(imports_ast) or imports
    except SyntaxError as exc:
        syntax_error = f"{exc.__class__.__name__}: {exc}"

    return StructureScan(
        line_count=line_count,
        imports=imports,
        defs=defs,
        classes=classes,
        calls=calls,
        has_main_guard=has_main_guard,
        syntax_error=syntax_error,
        entrypoint_candidates=entrypoint_candidates,
    )
