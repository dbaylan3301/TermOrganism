from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ConfidenceReport:
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    uncertainty: str = ""
    recommendation: str = "apply_with_review"
