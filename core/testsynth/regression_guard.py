from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RegressionGuardResult:
    ok: bool
    mode: str
    reason: str
    score: float = 0.0
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return (text or "").strip()


def check_failure_signature_removed(before_stderr: str, after_stderr: str) -> RegressionGuardResult:
    before = _normalize(before_stderr)
    after = _normalize(after_stderr)

    if before and not after:
        return RegressionGuardResult(
            ok=True,
            mode="failure_signature_removed",
            reason="previous stderr signature disappeared",
            score=0.60,
            details={"before": before, "after": after},
        )

    if before != after:
        return RegressionGuardResult(
            ok=True,
            mode="failure_signature_changed",
            reason="stderr signature changed after candidate execution",
            score=0.35,
            details={"before": before, "after": after},
        )

    return RegressionGuardResult(
        ok=False,
        mode="failure_signature_unchanged",
        reason="stderr signature unchanged",
        score=0.0,
        details={"before": before, "after": after},
    )


def check_expected_exception_absent(before_exception_type: str, after_stderr: str) -> RegressionGuardResult:
    exc = _normalize(before_exception_type)
    after = _normalize(after_stderr)

    if not exc:
        return RegressionGuardResult(
            ok=True,
            mode="exception_absence_skip",
            reason="no prior exception type available",
            score=0.0,
            details={"before_exception_type": exc},
        )

    if exc and exc not in after:
        return RegressionGuardResult(
            ok=True,
            mode="exception_absent",
            reason=f"previous exception type {exc!r} no longer present in stderr",
            score=0.40,
            details={"before_exception_type": exc, "after": after},
        )

    return RegressionGuardResult(
        ok=False,
        mode="exception_still_present",
        reason=f"previous exception type {exc!r} still present",
        score=0.0,
        details={"before_exception_type": exc, "after": after},
    )


def combine_regression_guards(*guards: RegressionGuardResult) -> RegressionGuardResult:
    ok = any(g.ok for g in guards)
    score = round(sum(g.score for g in guards if isinstance(g.score, (int, float))), 4)
    return RegressionGuardResult(
        ok=ok,
        mode="combined_regression_guard",
        reason="combined regression guards evaluated",
        score=score,
        details={"guards": [g.to_dict() for g in guards]},
    )
