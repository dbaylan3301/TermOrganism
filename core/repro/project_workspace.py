from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import shutil


@dataclass
class WorkspaceLayout:
    root: str
    workspace_root: str
    target_src: str
    target_dst: str
    project_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _guess_project_root(target: Path) -> Path:
    cur = target.resolve().parent
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}

    for base in [cur, *cur.parents]:
        if any((base / m).exists() for m in markers):
            return base

    return target.resolve().parent


def _copy_tree_filtered(src_root: Path, dst_root: Path) -> None:
    ignore_dirs = {
        "__pycache__", ".git", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", ".venv", "venv", "node_modules"
    }
    allow_suffixes = {".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".md"}

    for path in src_root.rglob("*"):
        rel = path.relative_to(src_root)

        if any(part in ignore_dirs for part in rel.parts):
            continue

        dst = dst_root / rel

        if path.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        if path.suffix.lower() in allow_suffixes or path.name in {"README", "LICENSE"}:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)


def build_temp_workspace(file_path: str | Path):
    target = Path(file_path).resolve()
    project_root = _guess_project_root(target)

    tmp = TemporaryDirectory(prefix="termorganism_project_ws_")
    workspace_root = Path(tmp.name) / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    _copy_tree_filtered(project_root, workspace_root)

    target_dst = workspace_root / target.relative_to(project_root)

    layout = WorkspaceLayout(
        root=tmp.name,
        workspace_root=str(workspace_root),
        target_src=str(target),
        target_dst=str(target_dst),
        project_root=str(project_root),
    )
    return tmp, layout
