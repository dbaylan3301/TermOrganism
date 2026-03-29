from __future__ import annotations

import tempfile
from pathlib import Path

from core.autofix import run_autofix
from core.salvage.dependency_infer import infer_dependencies
from core.salvage.intent_infer import infer_intent
from core.salvage.report import write_salvage_bundle
from core.salvage.structure_scan import scan_structure
from core.salvage.symbol_recover import recover_symbols
from core.salvage.syntax_recover import recover_syntax
from core.salvage.verifier import verify_candidate

try:
    from core.ui.thoughts import ThoughtEvent
except Exception:  # pragma: no cover
    ThoughtEvent = None


def _emit_thought(
    thought_bus,
    phase: str,
    message: str,
    *,
    kind: str = "info",
    confidence: float | None = None,
    file_path: str | None = None,
) -> None:
    if thought_bus is None or ThoughtEvent is None:
        return
    try:
        thought_bus.emit(
            ThoughtEvent(
                phase=phase,
                message=message,
                kind=kind,
                confidence=confidence,
                file_path=file_path,
            )
        )
    except Exception:
        return


def _extract_smoke_error_text(verification: dict) -> str:
    smoke = verification.get("smoke_run") or {}
    return str(smoke.get("stderr") or smoke.get("stdout") or "").strip()


def _same_single_target(temp_path: Path, hinted_target: str | None) -> bool:
    if not hinted_target:
        return True
    try:
        hinted = Path(hinted_target)
        return hinted.name == temp_path.name
    except Exception:
        return False


def _run_fallback_autofix(
    *,
    repaired_source: str,
    target_path: Path,
    initial_verification: dict,
    thought_bus=None,
) -> tuple[str, dict, dict]:
    error_text = _extract_smoke_error_text(initial_verification)
    if not error_text:
        return repaired_source, initial_verification, {
            "attempted": False,
            "reason": "no_smoke_error_text",
        }

    _emit_thought(
        thought_bus,
        "Fallback Expert",
        "compile-only result detected; invoking targeted autofix fallback",
        kind="warn",
        file_path=str(target_path),
    )

    with tempfile.TemporaryDirectory(prefix="termorganism_salvage_fallback_") as td:
        temp_path = Path(td) / target_path.name
        temp_path.write_text(repaired_source, encoding="utf-8")

        autofix_payload = run_autofix(
            error_text=error_text,
            file_path=str(temp_path),
            auto_apply=False,
            exec_suggestions=False,
            dry_run=True,
        )

    result = (autofix_payload or {}).get("result") or {}
    candidate_code = str(result.get("candidate_code") or "")
    hinted_target = result.get("target_file") or result.get("file_path_hint")
    target_match = _same_single_target(Path(target_path.name), hinted_target)

    fallback_info = {
        "attempted": True,
        "reason": "compile_only_autofix_fallback",
        "kind": result.get("kind"),
        "summary": result.get("summary"),
        "target_file": hinted_target,
        "candidate_present": bool(candidate_code),
        "target_match": target_match,
        "suggested_patch": result.get("patch"),
        "sandbox": (autofix_payload or {}).get("sandbox"),
        "behavioral_verify": (autofix_payload or {}).get("behavioral_verify"),
        "contract_result": (autofix_payload or {}).get("contract_result"),
    }

    _emit_thought(
        thought_bus,
        "Fallback Expert",
        f"selected kind={result.get('kind')} target={hinted_target}",
        kind="success" if candidate_code else "fail",
        file_path=hinted_target,
    )

    if candidate_code and target_match:
        final_source = candidate_code
        _emit_thought(
            thought_bus,
            "Fallback Rewrite",
            "applied autofix candidate source rewrite",
            kind="success",
            file_path=str(target_path),
        )
        final_verification = verify_candidate(final_source, str(target_path))
        fallback_info["applied_source_rewrite"] = True
        fallback_info["resulting_quality"] = final_verification.get("repair_quality")
        return final_source, final_verification, fallback_info

    fallback_info["applied_source_rewrite"] = False
    fallback_info["resulting_quality"] = initial_verification.get("repair_quality")
    return repaired_source, initial_verification, fallback_info


def run_salvage(
    target: str,
    *,
    deep: bool = False,
    out_dir: str | None = None,
    thought_bus=None,
) -> dict:
    target_path = Path(target).resolve()
    if not target_path.exists():
        return {
            "ok": False,
            "error": f"target does not exist: {target_path}",
        }

    _emit_thought(
        thought_bus,
        "Input",
        f"target={target_path}",
        kind="info",
        file_path=str(target_path),
    )

    original_source = target_path.read_text(encoding="utf-8", errors="replace")

    scan0 = scan_structure(original_source)
    _emit_thought(
        thought_bus,
        "Structure Scan",
        f"lines={scan0.line_count} imports={len(scan0.imports)} defs={len(scan0.defs)} classes={len(scan0.classes)} syntax_error={bool(scan0.syntax_error)}",
        kind="info",
        file_path=str(target_path),
    )

    syntax_source, syntax_changes = recover_syntax(original_source, deep=deep)
    scan1 = scan_structure(syntax_source)
    _emit_thought(
        thought_bus,
        "Syntax Recovery",
        f"changes={len(syntax_changes)} syntax_error_after={bool(scan1.syntax_error)}",
        kind="success" if not scan1.syntax_error else "warn",
        file_path=str(target_path),
    )

    symbol_source, symbol_changes = recover_symbols(syntax_source, deep=deep)
    scan2 = scan_structure(symbol_source)
    _emit_thought(
        thought_bus,
        "Symbol Recovery",
        f"changes={len(symbol_changes)} defs={len(scan2.defs)} classes={len(scan2.classes)}",
        kind="info",
        file_path=str(target_path),
    )

    intent = infer_intent(symbol_source, scan2.imports, scan2.defs)
    _emit_thought(
        thought_bus,
        "Intent Inference",
        f"summary={intent.get('summary')}",
        kind="info",
        file_path=str(target_path),
    )

    deps = infer_dependencies(scan2.imports)
    _emit_thought(
        thought_bus,
        "Dependency Inference",
        f"third_party={len((deps or {}).get('third_party') or [])} unresolved={len((deps or {}).get('unresolved_modules') or [])}",
        kind="info",
        file_path=str(target_path),
    )

    verification_initial = verify_candidate(symbol_source, str(target_path))
    _emit_thought(
        thought_bus,
        "Initial Verification",
        f"quality={verification_initial.get('repair_quality')} overall_ok={verification_initial.get('overall_ok')}",
        kind="success" if verification_initial.get("overall_ok") else "warn",
        file_path=str(target_path),
    )

    final_source = symbol_source
    verification_final = verification_initial
    fallback = {
        "attempted": False,
        "reason": "verification_not_compile_only",
    }

    if verification_initial.get("repair_quality") == "compile_only":
        final_source, verification_final, fallback = _run_fallback_autofix(
            repaired_source=symbol_source,
            target_path=target_path,
            initial_verification=verification_initial,
            thought_bus=thought_bus,
        )

    _emit_thought(
        thought_bus,
        "Final Verification",
        f"quality={verification_final.get('repair_quality')} overall_ok={verification_final.get('overall_ok')}",
        kind="success" if verification_final.get("overall_ok") else "fail",
        file_path=str(target_path),
    )

    payload = {
        "ok": True,
        "mode": "salvage",
        "deep": deep,
        "target_file": str(target_path),
        "intent": intent,
        "dependencies": deps,
        "structure_before": scan0.to_dict(),
        "structure_after_syntax": scan1.to_dict(),
        "structure_final": scan2.to_dict(),
        "recovery": {
            "syntax_changes": syntax_changes,
            "symbol_changes": symbol_changes,
        },
        "verification_initial": verification_initial,
        "fallback": fallback,
        "verification": verification_final,
        "salvage_status": verification_final.get("repair_quality"),
        "salvage_ok": bool(verification_final.get("overall_ok")),
    }

    artifacts = write_salvage_bundle(
        original_source=original_source,
        repaired_source=final_source,
        original_path=str(target_path),
        payload=payload,
        out_dir=out_dir,
    )
    payload["artifacts"] = artifacts

    _emit_thought(
        thought_bus,
        "Bundle Write",
        f"bundle_root={artifacts.get('bundle_root')}",
        kind="success",
    )

    return payload
