from __future__ import annotations

from typing import Any

from core.verify.sandbox import run_in_sandbox
from core.verify.contract_synth import synthesize_and_check_contract


def verify_plan(
    plan: dict[str, Any],
    file_path: str | None = None,
    error_text: str = "",
) -> dict[str, Any]:
    sandbox_result: dict[str, Any] = {}
    try:
        ctx = type("Ctx", (), {})()
        ctx.file_path = file_path
        sandbox_result = run_in_sandbox(plan, ctx)
    except Exception:
        sandbox_result = {"ok": False, "reason": "sandbox execution failed"}

    contract_result: dict[str, Any] = {}
    try:
        contract_result = synthesize_and_check_contract(
            before_error_text=error_text,
            branch_result=sandbox_result,
            expected_behavior=plan.get("expected_behavior", {}),
        )
    except Exception:
        contract_result = {"ok": False, "reason": "contract synthesis failed"}

    ok = bool(sandbox_result.get("ok")) and bool(contract_result.get("ok"))

    return {
        "ok": ok,
        "sandbox": sandbox_result,
        "contract": contract_result,
    }
