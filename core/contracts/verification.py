from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class VerificationResult:
    static_ok: bool
    behavioral_ok: bool
    sandbox_ok: bool | None = None
    contract_ok: bool | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    details: dict[str, Any] = field(default_factory=dict)
