from __future__ import annotations

import subprocess
from pathlib import Path


def get_diff(repo_path: str | Path, revspec: str = "HEAD") -> str:
    repo = Path(repo_path)
    return subprocess.check_output(["git", "diff", revspec], cwd=repo, text=True)
