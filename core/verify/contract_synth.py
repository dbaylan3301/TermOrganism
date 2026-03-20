from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ContractSynthesisResult:
    ok: bool
    reason: str
    checks: list[dict[str, Any]]
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def synthesize_and_check_contract(*, before_error_text: str, branch_result: dict[str, Any], expected_behavior: dict[str, Any] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    expected_behavior = expected_behavior or {}

    runtime = branch_result.get("runtime", {}) or {}
    stderr = runtime.get("stderr", "") or ""
    returncode = runtime.get("returncode", 1)

    total = 0.0

    exc = expected_behavior.get("exception_absent")
    if exc:
        ok = exc not in stderr
        checks.append({
            "name": "exception_absent",
            "ok": ok,
            "expected": exc,
        })
        total += 0.5 if ok else 0.0

    expected_exit = expected_behavior.get("exit_code")
    if expected_exit is not None:
        ok = returncode == expected_exit
        checks.append({
            "name": "exit_code",
            "ok": ok,
            "expected": expected_exit,
            "actual": returncode,
        })
        total += 0.5 if ok else 0.0

    ok_all = all(x["ok"] for x in checks) if checks else False
    reason = "contract checks passed" if ok_all else "contract checks failed"

    return ContractSynthesisResult(
        ok=ok_all,
        reason=reason,
        checks=checks,
        score=round(total, 4),
    ).to_dict()
