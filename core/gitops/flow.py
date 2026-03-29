from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from core.gitops.branching import create_repair_branch
from core.gitops.undo import create_undo_point, undo_to_ref


def find_repo_root(path: str | Path) -> Path | None:
    p = Path(path).resolve()
    start = p if p.is_dir() else p.parent
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            text=True,
        ).strip()
        return Path(out)
    except Exception:
        return None


def prepare_git_context(
    *,
    target_file: str | Path,
    use_branch: bool = False,
    use_undo: bool = False,
    branch_name: str | None = None,
) -> dict[str, Any]:
    repo_root = find_repo_root(target_file)
    if repo_root is None:
        return {
            "enabled": False,
            "reason": "not_git_repo",
        }

    result: dict[str, Any] = {
        "enabled": True,
        "repo_root": str(repo_root),
    }

    if use_undo:
        undo_ref = create_undo_point(repo_root)
        result["undo_ref"] = undo_ref

    if use_branch:
        if not branch_name:
            target_name = Path(target_file).stem.replace("_", "-")
            branch_name = f"termorganism/repair-{target_name}"
        created = create_repair_branch(repo_root, branch_name)
        result["branch"] = created

    return result


def run_git_undo(repo_or_target: str | Path, ref: str) -> dict[str, Any]:
    repo_root = find_repo_root(repo_or_target)
    if repo_root is None:
        return {
            "success": False,
            "error": "not_git_repo",
        }

    undo_to_ref(repo_root, ref)
    return {
        "success": True,
        "repo_root": str(repo_root),
        "undo_ref": ref,
    }
