from __future__ import annotations

from pathlib import Path
from typing import Any


def _canon(p: str | None) -> str | None:
    if not p:
        return None
    try:
        return str(Path(p).resolve())
    except Exception:
        return str(Path(p))


def build_multifile_plan_from_base(
    *,
    base_plan: dict[str, Any],
    file_path: str | None,
    semantic: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not file_path:
        return None

    semantic_loc = ((semantic or {}).get("localization") or {}) if isinstance(semantic, dict) else {}
    items = semantic_loc.get("items", []) or []

    caller = _canon(file_path)
    provider = None

    for item in items:
        fp = item.get("file_path")
        if not fp:
            continue

        fp_canon = _canon(fp)
        if not fp_canon or not fp_canon.endswith(".py"):
            continue
        if "/usr/lib/" in fp_canon:
            continue
        if fp_canon == caller:
            continue

        provider = fp_canon
        break

    if not provider:
        return None

    edits = list(base_plan.get("edits", []) or [])
    if not edits:
        return None

    first = dict(edits[0])
    first["file"] = provider

    new_plan = dict(base_plan)
    new_plan["plan_id"] = f"{base_plan.get('plan_id', 'plan')}_multifile"
    new_plan["hypothesis"] = "provider/caller contract is broken across files; repair provider-side behavior first"
    new_plan["target_files"] = [provider, caller]
    new_plan["edits"] = [first]
    new_plan["confidence"] = max(float(base_plan.get("confidence", 0.0) or 0.0), 0.90)
    new_plan["risk"] = max(float(base_plan.get("risk", 0.12) or 0.12), 0.14)
    new_plan["blast_radius"] = max(float(base_plan.get("blast_radius", 0.0) or 0.0), 0.16)

    evidence = dict(new_plan.get("evidence", {}) or {})
    evidence["multifile"] = True
    evidence["caller"] = caller
    evidence["provider"] = provider
    new_plan["evidence"] = evidence

    return new_plan


def expand_multifile_plan_family(
    *,
    base_plans: list[dict[str, Any]],
    file_path: str | None,
    semantic: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for plan in base_plans or []:
        mf = build_multifile_plan_from_base(
            base_plan=plan,
            file_path=file_path,
            semantic=semantic,
        )
        if not mf:
            continue

        plan_id = str(mf.get("plan_id", ""))
        if plan_id in seen_ids:
            continue
        seen_ids.add(plan_id)
        expanded.append(mf)

    return expanded
