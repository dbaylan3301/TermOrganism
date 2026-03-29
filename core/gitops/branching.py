from __future__ import annotations

import subprocess
from pathlib import Path


def create_repair_branch(repo_path: str | Path, branch_name: str) -> str:
    repo = Path(repo_path)
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo, check=True)
    return branch_name
