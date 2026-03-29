from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime


def create_undo_point(repo_path: str | Path, prefix: str = "termorganism/undo") -> str:
    repo = Path(repo_path)
    ref = f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    subprocess.run(["git", "tag", ref], cwd=repo, check=True)
    return ref


def undo_to_ref(repo_path: str | Path, ref: str) -> None:
    repo = Path(repo_path)
    subprocess.run(["git", "reset", "--hard", ref], cwd=repo, check=True)
