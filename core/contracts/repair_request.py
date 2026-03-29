from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RepairRequest:
    target_file: str
    error_text: str
    language: str = "python"
    mode: str = "repair"          # repair | salvage | verify
    fast: bool = False
    deep: bool = False
    force_semantic: bool = False
    auto_apply: bool = False
    exec_suggestions: bool = False
    dry_run: bool = True
