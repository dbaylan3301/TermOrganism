from __future__ import annotations

from typing import Any


def _normalize_strategy(candidate: dict[str, Any]) -> str:
    metadata = dict(candidate.get("metadata", {}) or {})
    strategy = str(metadata.get("strategy", "") or "").strip()
    if strategy:
        return strategy

    code = str(candidate.get("candidate_code", "") or "")
    summary = str(candidate.get("summary", "") or "")
    hypothesis = str(candidate.get("hypothesis", "") or "")
    blob = " ".join([code, summary, hypothesis])

    if 'exists() else ""' in code or "exists() fallback" in blob:
        return "guard_exists"
    if "except FileNotFoundError" in code or "FileNotFoundError recovery" in blob:
        return "try_except_recovery"
    if (candidate.get("patch") and not code.strip()) or "create missing runtime path" in blob:
        return "touch_only"
    return "unknown"


def _candidate_to_plan(candidate: dict[str, Any], file_path: str | None) -> dict[str, Any]:
    metadata = dict(candidate.get("metadata", {}) or {})
    strategy = _normalize_strategy(candidate)

    target_file = (
        candidate.get("target_file")
        or candidate.get("file_path_hint")
        or file_path
    )

    patch = candidate.get("patch")
    candidate_code = str(candidate.get("candidate_code", "") or "")
    summary = str(candidate.get("summary", "") or "")
    hypothesis = str(candidate.get("hypothesis", "") or "")
    semantic_claim = str(candidate.get("semantic_claim", "") or "")

    if strategy == "touch_only":
        edit = {
            "file": target_file,
            "kind": "operational",
            "summary": summary or "operational fix",
            "commands": metadata.get("shell_steps", []) or ([patch] if patch else []),
            "candidate_code": "",
        }
    else:
        edit = {
            "file": target_file,
            "kind": "replace_full",
            "summary": summary or "code repair",
            "candidate_code": candidate_code,
        }

    expected_behavior = {
        "exception_absent": "FileNotFoundError",
        "exit_code": 0,
    }

    return {
        "plan_id": f"plan_{strategy}_{abs(hash((target_file, summary, strategy, candidate_code))) % 100000}",
        "hypothesis": hypothesis,
        "semantic_claim": semantic_claim,
        "root_cause_nodes": [],
        "target_files": [target_file] if target_file else [],
        "edits": [edit],
        "expected_behavior": expected_behavior,
        "evidence": {
            "strategy": strategy,
            "localization_target": target_file,
            "source_candidate_summary": summary,
        },
        "confidence": float(candidate.get("confidence", 0.0) or 0.0),
        "risk": float(candidate.get("blast_radius", 0.0) or 0.0),
        "blast_radius": float(candidate.get("blast_radius", 0.0) or 0.0),
    }


def build_repair_plans(
    *,
    error_text: str,
    semantic: dict[str, Any] | None,
    causes: list[dict[str, Any]] | None,
    project_graph: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None = None,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []

    for cand in candidates or []:
        if not isinstance(cand, dict):
            continue
        plans.append(_candidate_to_plan(cand, file_path=file_path))

    if plans:
        return plans

    target = file_path
    return [{
        "plan_id": "plan_runtime_operational_fallback",
        "hypothesis": "missing path may be sufficient; create runtime file path without source edits",
        "root_cause_nodes": [],
        "target_files": [target] if target else [],
        "edits": [{
            "file": target,
            "kind": "operational",
            "summary": "create missing runtime path",
            "commands": ["mkdir -p logs", "touch logs/app.log"],
            "candidate_code": "",
        }],
        "expected_behavior": {
            "exception_absent": "FileNotFoundError",
            "exit_code": 0,
        },
        "evidence": {
            "strategy": "touch_only",
            "localization_target": target,
        },
        "confidence": 0.66,
        "risk": 0.08,
        "blast_radius": 0.05,
    }]
