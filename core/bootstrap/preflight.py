from __future__ import annotations

import ast
import py_compile
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]

BOOTSTRAP_SEED_RELATIVE_PATHS = [
    "termorganism",
    "termorganism-safe",
    "core/bootstrap/self_heal.py",
    "core/cli/autofix_cli.py",
    "core/autofix.py",
    "core/ui/thoughts.py",
    "core/ui/rich_sink.py",
    "core/verify/__init__.py",
    "core/verify/microvm.py",
    "core/verify/sandbox_router.py",
    "core/memory/__init__.py",
    "core/memory/engine.py",
]


@dataclass
class PreflightFailure:
    file_path: str
    line_no: int | None
    message: str
    exception_type: str


def _parse_line_no(msg: str) -> int | None:
    pats = [
        r"line (\d+)",
        r"\((?:[^\n]*?), line (\d+)\)",
    ]
    for pat in pats:
        m = re.search(pat, msg)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None


def _iter_python_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if "/__pycache__/" in f"/{rel}/":
            continue
        if rel.startswith(".git/") or rel.startswith(".venv/") or rel.startswith("venv/"):
            continue
        if p.suffix == ".py":
            yield p


def _module_name_for_path(root: Path, path: Path) -> str | None:
    rel = path.relative_to(root).as_posix()
    if not rel.endswith(".py"):
        return None
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([p for p in parts if p])


def _module_index(root: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    for p in _iter_python_files(root):
        mod = _module_name_for_path(root, p)
        if mod:
            idx[mod] = p
    return idx


def _resolve_from_import(current_mod: str, level: int, module: str | None) -> str:
    if not level:
        return module or ""
    pkg = current_mod.split(".")
    if current_mod and not current_mod.endswith("__init__") and len(pkg) > 1:
        pkg = pkg[:-1]
    hops = max(0, level - 1)
    if hops <= len(pkg):
        pkg = pkg[: len(pkg) - hops]
    else:
        pkg = []
    if module:
        pkg = pkg + module.split(".")
    return ".".join([x for x in pkg if x])


def _local_import_targets(root: Path, path: Path, index: dict[str, Path]) -> list[Path]:
    if path.suffix != ".py":
        return []

    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []

    out: list[Path] = []
    current_mod = _module_name_for_path(root, path) or ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                if mod in index:
                    out.append(index[mod])
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_import(current_mod, int(node.level or 0), node.module)
            if base in index:
                out.append(index[base])
            for alias in node.names:
                cand = f"{base}.{alias.name}" if base else alias.name
                if cand in index:
                    out.append(index[cand])

    # de-dupe preserve order
    seen = set()
    deduped = []
    for p in out:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            deduped.append(p)
    return deduped


def discover_critical_files(root: Path | None = None) -> list[Path]:
    root = root or ROOT
    index = _module_index(root)

    seeds: list[Path] = []
    for rel in BOOTSTRAP_SEED_RELATIVE_PATHS:
        p = root / rel
        if p.exists():
            seeds.append(p)

    seen = {str(p.resolve()) for p in seeds}
    queue = list(seeds)
    out = list(seeds)

    while queue:
        cur = queue.pop(0)
        for dep in _local_import_targets(root, cur, index):
            key = str(dep.resolve())
            if key not in seen:
                seen.add(key)
                out.append(dep)
                queue.append(dep)

    return sorted(out, key=lambda p: p.as_posix())


def preflight_compile_graph(root: Path | None = None) -> list[PreflightFailure]:
    root = root or ROOT
    failures: list[PreflightFailure] = []
    for p in discover_critical_files(root):
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as exc:
            failures.append(
                PreflightFailure(
                    file_path=str(p),
                    line_no=_parse_line_no(str(exc)),
                    message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
    return failures


def main() -> int:
    files = discover_critical_files(ROOT)
    failures = preflight_compile_graph(ROOT)

    print(f"[bootstrap-preflight] files={len(files)}")
    if failures:
        print(f"[bootstrap-preflight] failures={len(failures)}")
        for item in failures:
            print(asdict(item))
        return 1

    print("[bootstrap-preflight] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
