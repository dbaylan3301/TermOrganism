from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RepairKind = Literal["syntax", "dependency", "runtime", "memory", "llm", "hybrid"]


@dataclass(slots=True)
class FailureContext:
    file_path: str
    language: str
    command: list[str]
    cwd: str
    source_code: str
    stdout: str
    stderr: str
    exit_code: int
    exception_type: str | None = None
    context_tags: list[str] = field(default_factory=list)
    project_facts: dict[str, Any] = field(default_factory=dict)
    memory_features: dict[str, Any] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RepairCandidate:
    expert_name: str
    kind: RepairKind
    patched_code: str | None
    patch_unified_diff: str
    rationale: str
    router_score: float = 0.0
    expert_score: float = 0.0
    memory_prior: float = 0.0
    patch_safety_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VerificationResult:
    ok: bool
    compile_ok: bool
    run_ok: bool
    tests_ok: bool
    score: float
    stdout: str
    stderr: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RankedCandidate:
    candidate: RepairCandidate
    verification: VerificationResult
    final_score: float


@dataclass(slots=True)
class RoutingDecision:
    expert_name: str
    score: float
    reasons: list[str] = field(default_factory=list)
