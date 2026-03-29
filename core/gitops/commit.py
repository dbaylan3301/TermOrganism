from __future__ import annotations

import subprocess
from pathlib import Path


def create_commit(repo_path: str | Path, message: str, add_all: bool = True) -> str:
    repo = Path(repo_path)
    if add_all:
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    return sha
