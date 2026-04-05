from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from core.watch.predictive_runtime import analyze_python_file, analyze_python_text


def _fingerprint(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8", "ignore")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-live")
    parser.add_argument("file", nargs="?", help="İzlenecek Python dosyası")
    parser.add_argument("--stdin", action="store_true", help="Metni stdin'den al ve bir kez analiz et")
    parser.add_argument("--interval", type=float, default=0.35, help="Loop aralığı")
    parser.add_argument("--ndjson", action="store_true", help="NDJSON çıktı ver")
    args = parser.parse_args()

    if args.stdin:
        import sys
        text = sys.stdin.read()
        payload = analyze_python_text(text, file_path=args.file or "<buffer>")
        print(json.dumps(payload, ensure_ascii=False) if args.ndjson else json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not args.file:
        raise SystemExit("file gerekli")

    target = Path(args.file).expanduser().resolve()
    last_fp = ""
    last_mtime = None

    try:
        while True:
            if not target.exists():
                payload = analyze_python_text("", file_path=str(target))
            else:
                mtime = target.stat().st_mtime
                if last_mtime is not None and mtime == last_mtime:
                    time.sleep(max(0.1, args.interval))
                    continue
                last_mtime = mtime
                payload = analyze_python_file(str(target))

            fp = _fingerprint(payload)
            if fp != last_fp:
                if args.ndjson:
                    print(json.dumps(payload, ensure_ascii=False), flush=True)
                else:
                    top = payload.get("top_whisper") or "sessiz"
                    print(f"\n[{target.name}] {top}", flush=True)
                    for item in payload.get("diagnostics", [])[:8]:
                        print(f"- {item['kind']} p={item['priority']} :: {item['message']}", flush=True)
                last_fp = fp

            time.sleep(max(0.1, args.interval))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
