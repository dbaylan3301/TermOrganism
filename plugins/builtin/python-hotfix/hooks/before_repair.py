#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> int:
    data = json.load(sys.stdin)
    payload = data.get("payload", {})
    file_path = str(payload.get("file", ""))

    if "hook_block" in file_path:
        result = {
            "ok": True,
            "action": "block",
            "source": "python-hotfix",
            "event": data.get("event"),
            "reason": "hook_block_pattern_matched",
            "note": f"repair blocked for {file_path}",
        }
        sys.stdout.write(json.dumps(result))
        return 0

    result = {
        "ok": True,
        "action": "annotate",
        "source": "python-hotfix",
        "event": data.get("event"),
        "note": f"pre-repair hook for {file_path or '<unknown>'}",
    }
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
