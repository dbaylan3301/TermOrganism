from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from core.watch.predictive_runtime import analyze_python_file


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-sidebar")
    parser.add_argument("file")
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    target = Path(args.file).expanduser().resolve()
    last_mtime = None

    while True:
        if not target.exists():
            payload = {"file": str(target), "top_whisper": "dosya yok", "diagnostics": []}
        else:
            mtime = target.stat().st_mtime
            if not args.once and last_mtime is not None and mtime == last_mtime:
                time.sleep(max(0.1, args.interval))
                continue
            last_mtime = mtime
            payload = analyze_python_file(str(target))

        top = payload.get("top_whisper") or "sessiz"
        diagnostics = payload.get("diagnostics", [])
        out = {
            "file": str(target),
            "top_whisper": top,
            "count": len(diagnostics),
            "diagnostics": diagnostics[:8],
        }
        print(json.dumps(out, ensure_ascii=False), flush=True)

        if args.once:
            return 0

        time.sleep(max(0.1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
