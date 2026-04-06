from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class TaskSpec:
    raw_message: str
    intent_family: str
    user_goal: str
    target_scope: str = "repo"
    operation_mode: str = "read_only"   # read_only | preview_first | execute
    risk_level: str = "low"             # low | medium | high
    needs_repo_context: bool = True
    needs_execution: bool = False
    needs_clarification: bool = False
    ambiguity_note: str = ""
    recommended_route: str = "semantic_readonly"
    confidence: float = 0.6
    constraints: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    language: str = "tr"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
