from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import os
import shutil
from tempfile import TemporaryDirectory


@dataclass
class WorkspaceLayout:
    root: str
    workspace_root: str
    target_src: str
    target_dst: str
    project_root: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_IGNORE_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".idea",
    ".vscode",
    ".tox",
    ".nox",
    "dist",
    "build",
    ".eggs",
}

_IGNORE_REL_PATHS = {
    Path("benchmarks/results"),
}


def _guess_project_root(target: Path) -> Path:
    target = target.resolve()
    cur = target.parent if target.is_file() else target
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}

    for base in [cur, *cur.parents]:
        if any((base / marker).exists() for marker in markers):
            return base

    return cur


def _should_skip(rel_path: Path) -> bool:
    if rel_path == Path("."):
        return False
    if any(part in _IGNORE_NAMES for part in rel_path.parts):
        return True
    return any(rel_path == p or p in rel_path.parents for p in _IGNORE_REL_PATHS)


def _copy_tree_filtered(src_root: Path, dst_root: Path) -> None:
    src_root = Path(src_root).resolve()
    dst_root = Path(dst_root).resolve()
    dst_root.mkdir(parents=True, exist_ok=True)

    for root, dirnames, filenames in os.walk(src_root, topdown=True, followlinks=False):
        root_path = Path(root)
        rel_root = root_path.relative_to(src_root)

        if _should_skip(rel_root):
            dirnames[:] = []
            continue

        kept_dirs: list[str] = []
        for dirname in dirnames:
            src_dir = root_path / dirname
            rel_dir = rel_root / dirname if rel_root != Path(".") else Path(dirname)

            if _should_skip(rel_dir):
                continue

            try:
                if src_dir.is_symlink():
                    continue
            except OSError:
                continue

            kept_dirs.append(dirname)

        dirnames[:] = kept_dirs

        dest_root = dst_root / rel_root if rel_root != Path(".") else dst_root
        dest_root.mkdir(parents=True, exist_ok=True)

        for filename in filenames:
            src_file = root_path / filename
            rel_file = rel_root / filename if rel_root != Path(".") else Path(filename)

            if _should_skip(rel_file):
                continue

            try:
                if src_file.is_symlink() or not src_file.is_file():
                    continue
            except OSError:
                continue

            dest_file = dst_root / rel_file
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copyfile(src_file, dest_file)
            except OSError:
                continue


def build_temp_workspace(file_path: str | Path):
    file_path = Path(file_path).resolve()
    project_root = _guess_project_root(file_path)

    tmp = TemporaryDirectory(prefix="termorganism_workspace_")
    workspace_root = Path(tmp.name)

    _copy_tree_filtered(project_root, workspace_root)

    try:
        rel_target = file_path.relative_to(project_root)
    except ValueError:
        rel_target = Path(file_path.name)
        if file_path.is_file():
            dest_file = workspace_root / rel_target
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file_path, dest_file)

    target_dst = workspace_root / rel_target

    layout = WorkspaceLayout(
        root=str(workspace_root),
        workspace_root=str(workspace_root),
        target_src=str(file_path),
        target_dst=str(target_dst),
        project_root=str(project_root),
    )

    return tmp, layout
