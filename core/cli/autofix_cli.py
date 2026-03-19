from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from core.autofix import run_autofix


def detect_error_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".py":
        proc = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return (proc.stderr or proc.stdout).strip()
        return ""

    return file_path.read_text(encoding="utf-8", errors="replace").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="termorganism-autofix",
        description="Run TermOrganism autofix pipeline on a target file.",
    )
    parser.add_argument(
        "target",
        help="Target file path. Python file or a text file containing an error log.",
    )
    parser.add_argument(
        "--error-text",
        help="Explicit error text. If omitted, CLI will try to derive it from target.",
        default=None,
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        help="Apply eligible fixes to the target file after verification.",
    )
    parser.add_argument(
        "--exec",
        dest="exec_suggestions",
        action="store_true",
        help="Execute only whitelisted shell suggestions for executable shell candidates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --exec, only show what would run without executing it.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON result.",
    )
    return parser


def summarize(result: dict) -> str:
    lines: list[str] = []

    candidate = result.get("result") or {}
    if not isinstance(candidate, dict):
        candidate = {"raw": str(candidate)}

    lines.append("TermOrganism Autofix Result")
    lines.append("=" * 32)
    lines.append(f"expert      : {candidate.get('expert', '-')}")
    lines.append(f"kind        : {candidate.get('kind', '-')}")
    lines.append(f"confidence  : {candidate.get('confidence', '-')}")
    lines.append(f"summary     : {candidate.get('summary', '-')}")
    lines.append(f"verify      : {result.get('verify', {}).get('ok', '-')}")
    lines.append(f"verify_note : {result.get('verify', {}).get('reason', '-')}")
    lines.append(f"sandbox     : {result.get('sandbox', {}).get('ok', '-')}")
    lines.append(f"routes      : {', '.join(result.get('routes', [])) if result.get('routes') else '-'}")

    apply_info = result.get("apply")
    if isinstance(apply_info, dict):
        lines.append(f"applied     : {apply_info.get('applied', False)}")
        lines.append(f"apply_note  : {apply_info.get('reason', '-')}")
        lines.append(f"backup_path : {apply_info.get('backup_path', '-')}")

    exec_info = result.get("exec")
    if isinstance(exec_info, dict):
        lines.append(f"exec_done   : {exec_info.get('executed', False)}")
        lines.append(f"exec_dryrun : {exec_info.get('dry_run', False)}")
        lines.append(f"exec_all_ok : {exec_info.get('all_allowed', '-')}")

    patch = candidate.get("patch")
    if isinstance(patch, str) and patch.strip():
        lines.append("")
        lines.append("patch:")
        lines.append(patch)

    metadata = candidate.get("metadata")
    if isinstance(metadata, dict) and metadata.get("suggestions"):
        lines.append("")
        lines.append("suggestions:")
        for s in metadata["suggestions"]:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"HATA: hedef dosya bulunamadı: {target}", file=sys.stderr)
        return 2

    error_text = args.error_text
    if not error_text:
        error_text = detect_error_text(target)

    if not error_text:
        if args.json:
            print(json.dumps({
                "ok": True,
                "message": "No error detected. Target appears healthy.",
                "target": str(target),
                "changed": False,
            }, ensure_ascii=False, indent=2))
        else:
            print("Hata tespit edilmedi. Dosya zaten düzeltilmiş veya çalışır durumda.")
        return 0

    result = run_autofix(
        error_text=error_text,
        file_path=str(target),
        auto_apply=args.auto_apply,
        exec_suggestions=args.exec_suggestions,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(summarize(result))

    verify_ok = bool((result.get("verify") or {}).get("ok", False))
    return 0 if verify_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
