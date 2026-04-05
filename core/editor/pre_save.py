from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.watch.predictive_runtime import analyze_python_file, analyze_python_text


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-pre-save")
    parser.add_argument("file")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--block-on-error", action="store_true")
    args = parser.parse_args()

    target = Path(args.file).expanduser().resolve()

    if args.stdin:
        text = sys.stdin.read()
        payload = analyze_python_text(text, file_path=str(target))
    else:
        payload = analyze_python_file(str(target))

    diagnostics = payload.get("diagnostics", [])
    has_error = any(d.get("severity") == "error" for d in diagnostics)
    has_warning = any(d.get("severity") == "warning" for d in diagnostics)

    result = {
        "file": str(target),
        "top_whisper": payload.get("top_whisper", ""),
        "diagnostics": diagnostics,
        "allow_save": not (args.block_on_error and has_error),
        "has_error": has_error,
        "has_warning": has_warning,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[pre-save] {result['top_whisper'] or 'sessiz'}")
        for d in diagnostics[:8]:
            print(f"- {d['severity']} {d['kind']} p={d['priority']} :: {d['message']}")

    if args.block_on_error and has_error:
        return 4
    if has_warning:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
