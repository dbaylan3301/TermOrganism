from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FailureContext:
    error_text: str
    file_path: str | None = None
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""
    source_code: str = ""
    filename: str | None = None
    error_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepairCandidate:
    expert_name: str
    kind: str
    patched_code: str = ""
    patch_unified_diff: str | None = None
    rationale: str = ""
    router_score: float = 0.0
    expert_score: float = 0.0
    memory_prior: float = 0.0
    patch_safety_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RankedCandidate:
    candidate: Any
    final_score: float
    score_breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    ok: bool
    reason: str
    mode: str = ""
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticRepairCandidate:
    expert: str
    kind: str
    confidence: float
    summary: str
    candidate_code: str = ""
    patch: str | None = None
    hypothesis: str = ""
    semantic_claim: str = ""
    affected_scope: list[str] = field(default_factory=list)
    repro_fix_score: float = 0.0
    regression_score: float = 0.0
    blast_radius: float = 0.0
    risk: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
