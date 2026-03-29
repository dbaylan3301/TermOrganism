from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass(slots=True)
class PluginManifest:
    name: str
    version: str
    description: str = ""
    skills: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    enabled_by_default: bool = False
    root_dir: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> "PluginManifest":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        data.setdefault("root_dir", str(p.parent))
        return cls(**data)
