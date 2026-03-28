from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from core.contracts.verification import VerificationResult
from core.contracts.confidence import ConfidenceReport

@dataclass
class RepairResult:
    status: str                    # failed | compile_only | smoke_passed | verified
    target_file: str
    kind: str = ""
    summary: str = ""
    candidate_code: str = ""
    verification: VerificationResult | None = None
    confidence: ConfidenceReport | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
