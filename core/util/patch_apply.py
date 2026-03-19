from __future__ import annotations

from pathlib import Path
from datetime import datetime


def make_backup(target_path: str | Path) -> Path:
    p = Path(target_path)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup = p.with_name(f"{p.name}.bak.{ts}")
    backup.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return backup


def apply_text_replacement(target_path: str | Path, new_text: str) -> None:
    p = Path(target_path)
    p.write_text(new_text, encoding="utf-8")


def restore_backup(target_path: str | Path, backup_path: str | Path) -> None:
    target = Path(target_path)
    backup = Path(backup_path)
    target.write_text(backup.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
