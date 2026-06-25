from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def force_plan_target_to_file(plan: dict[str, Any], file_path: str | None) -> dict[str, Any]:
    if not isinstance(plan, dict) or not file_path:
        return plan

    try:
        fp_path = Path(file_path).resolve()
        fp = str(fp_path)
    except Exception:
        fp_path = Path(str(file_path))
        fp = str(file_path)

    if not fp:
        return plan

    parent_fp = str(fp_path.parent)

    def _looks_like_directory_target(x: Any) -> bool:
        s = str(x) if x is not None else ""
        if s in {"", ".", parent_fp}:
            return True
        try:
            xp = Path(s)
            if xp.exists() and xp.is_dir():
                return True
        except Exception:
            pass
        return False

    target_files = plan.get("target_files")
    if not isinstance(target_files, list) or not target_files or any(_looks_like_directory_target(x) for x in target_files):
        plan["target_files"] = [fp]

    affected_scope = plan.get("affected_scope")
    if isinstance(affected_scope, list):
        if not affected_scope or any(_looks_like_directory_target(x) for x in affected_scope):
            plan["affected_scope"] = [fp]

    edits = plan.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                cur = edit.get("file")
                if _looks_like_directory_target(cur):
                    edit["file"] = fp

    evidence = plan.get("evidence")
    if isinstance(evidence, dict):
        loc = evidence.get("localization_target")
        if _looks_like_directory_target(loc):
            evidence["localization_target"] = fp

    for key in ("target_file", "file_path_hint"):
        cur = plan.get(key)
        if _looks_like_directory_target(cur):
            plan[key] = fp

    return plan


def resolve_semantic_target(file_path: str | None, semantic: dict[str, Any] | None) -> str | None:
    loc = (semantic or {}).get("localization") or {}
    top = loc.get("top") or {}
    top_file = top.get("file_path")
    if top_file and str(top_file).endswith(".py") and "/usr/lib/" not in str(top_file):
        return str(Path(top_file).resolve())
    return file_path


def infer_provider_from_imports(file_path: str | None) -> str | None:
    if not file_path or not str(file_path).endswith(".py"):
        return None
    p = Path(file_path)
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return None
    root = p.parent
    candidates: list[Path] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                mod_path = root / (node.module.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                mod_path = root / (alias.name.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)
    if not candidates:
        return None
    for c in candidates:
        if c.name != p.name:
            return str(c.resolve())
    return str(candidates[0].resolve())


def build_semantic_prelude(error_text: str, file_path: str | None) -> dict[str, Any]:
    from core.repro.harness import run_python_file, run_shell_text
    from core.semantic.fault_localizer import localize_fault, summarize_suspicions

    forced = "FORCED_SEMANTIC_ANALYSIS" in (error_text or "")

    if file_path and str(file_path).endswith(".py") and not forced:
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
        }

    if forced and file_path and str(file_path).endswith(".py"):
        caller = str(Path(file_path).resolve())
        provider = infer_provider_from_imports(file_path)
        items = [{
            "file_path": caller,
            "line_no": None,
            "symbol": None,
            "reason": "forced semantic caller seed",
            "score": 0.91,
        }]
        if provider:
            items.append({
                "file_path": provider,
                "line_no": None,
                "symbol": None,
                "reason": "forced semantic provider seed",
                "score": 0.97,
            })
        return {
            "repro": {
                "ok": True,
                "command": [],
                "cwd": str(Path(file_path).resolve().parent),
                "returncode": 0,
                "stdout": "",
                "stderr": error_text,
                "exception_type": "ForcedSemanticAnalysis",
                "reproduced": False,
            },
            "localization": {
                "count": len(items),
                "top": items[1] if len(items) > 1 else items[0],
                "items": items,
            },
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict(),
        "localization": summarize_suspicions(suspicions),
    }
