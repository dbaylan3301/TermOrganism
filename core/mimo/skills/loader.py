from __future__ import annotations

from pathlib import Path
from typing import Any


def load_skill(name: str) -> str | None:
    skill_dir = Path.home() / ".local" / "share" / "mimocode" / "compose" / "skills"
    skill_file = skill_dir / name / "SKILL.md"
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")
    return None
