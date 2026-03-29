#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> int:
    data = json.load(sys.stdin)
    payload = data.get("payload", {})
    result = {
        "ok": True,
        "action": "annotate",
        "source": "python-hotfix",
        "event": data.get("event"),
        "note": f"pre-repair hook for {payload.get('file', '<unknown>')}",
    }
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
