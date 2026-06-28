"""Enhanced REPL commands for TermOrganism."""

from __future__ import annotations
import subprocess
from pathlib import Path


def run_git_command(args: list[str], cwd: str = ".") -> str:
    """Execute git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git hatası: {e}"


def get_repo_summary(cwd: str = ".") -> str:
    """Get repository summary."""
    lines = []
    
    readme = Path(cwd) / "README.md"
    if readme.exists():
        with open(readme, "r", encoding="utf-8") as f:
            first_lines = f.readlines()[:10]
            lines.append("".join(first_lines[:3]).strip())
    
    py_files = list(Path(cwd).rglob("*.py"))
    ts_files = list(Path(cwd).rglob("*.ts"))
    js_files = list(Path(cwd).rglob("*.js"))
    
    lines.append(f"\n📊 İstatistikler:")
    lines.append(f"  Python: {len(py_files)} dosya")
    lines.append(f"  TypeScript: {len(ts_files)} dosya")
    lines.append(f"  JavaScript: {len(js_files)} dosya")
    
    return "\n".join(lines)


def get_repo_status(cwd: str = ".") -> str:
    """Get repository status."""
    lines = ["📊 Repo Durumu:\n"]
    
    branch = run_git_command(["branch", "--show-current"], cwd)
    lines.append(f"Branch: {branch.strip()}")
    
    status = run_git_command(["status", "--short"], cwd)
    if status.strip():
        lines.append(f"\nDeğişiklikler:\n{status}")
    else:
        lines.append("\n✅ Working tree temiz")
    
    commits = run_git_command(["log", "--oneline", "-5"], cwd)
    if commits.strip():
        lines.append(f"\nSon 5 commit:\n{commits}")
    
    return "\n".join(lines)
