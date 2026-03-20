from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import ast


@dataclass
class FileNode:
    path: str
    imports: list[str]
    functions: list[str]
    classes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectGraph:
    project_root: str
    files: list[FileNode]
    adjacency: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "files": [f.to_dict() for f in self.files],
            "adjacency": self.adjacency,
        }


def _guess_project_root(file_path: str | Path | None) -> Path:
    if not file_path:
        return Path.cwd()
    p = Path(file_path).resolve()
    cur = p.parent if p.is_file() else p
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}
    for base in [cur, *cur.parents]:
        if any((base / m).exists() for m in markers):
            return base
    return cur


def _parse_python_file(path: Path) -> FileNode:
    text = path.read_text(encoding="utf-8", errors="replace")
    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []

    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
    except Exception:
        pass

    return FileNode(
        path=str(path),
        imports=sorted(set(imports)),
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
    )


def build_project_graph(file_path: str | Path | None) -> ProjectGraph:
    root = _guess_project_root(file_path)
    py_files = sorted(root.rglob("*.py"))

    files: list[FileNode] = []
    file_names = {p.stem: str(p) for p in py_files}
    adjacency: dict[str, list[str]] = {}

    for py in py_files:
        node = _parse_python_file(py)
        files.append(node)

        neighbors: list[str] = []
        for imp in node.imports:
            base = imp.split(".")[0]
            if base in file_names:
                neighbors.append(file_names[base])
        adjacency[str(py)] = sorted(set(neighbors))

    return ProjectGraph(
        project_root=str(root),
        files=files,
        adjacency=adjacency,
    )
