from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path

def write_salvage_bundle(
    *,
    original_source: str,
    repaired_source: str,
    original_path: str,
    payload: dict,
    out_dir: str | None = None,
) -> dict:
    src_path = Path(original_path).resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if out_dir:
        root = Path(out_dir).resolve()
    else:
        root = src_path.parent / "salvage" / f"{src_path.stem}_salvage_{stamp}"

    root.mkdir(parents=True, exist_ok=True)

    repaired_path = root / f"repaired_{src_path.name}"
    req_path = root / "inferred_requirements.txt"
    report_path = root / "salvage_report.json"
    diff_path = root / "salvage_diff.patch"

    repaired_path.write_text(repaired_source, encoding="utf-8")

    deps = (payload.get("dependencies") or {}).get("third_party") or []
    req_path.write_text("\n".join(deps) + ("\n" if deps else ""), encoding="utf-8")

    diff = "".join(difflib.unified_diff(
        original_source.splitlines(True),
        repaired_source.splitlines(True),
        fromfile=str(src_path),
        tofile=str(repaired_path),
    ))
    diff_path.write_text(diff, encoding="utf-8")

    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "bundle_root": str(root),
        "repaired_file": str(repaired_path),
        "inferred_requirements": str(req_path),
        "salvage_report": str(report_path),
        "salvage_diff": str(diff_path),
    }
