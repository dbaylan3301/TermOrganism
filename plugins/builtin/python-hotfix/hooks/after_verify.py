#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> int:
    data = json.load(sys.stdin)
    payload = data.get("payload", {})
    result_payload = payload.get("result", {}) if isinstance(payload, dict) else {}
    success = bool(result_payload.get("success")) or bool((result_payload.get("verify") or {}).get("ok"))
    result = {
        "ok": True,
        "action": "annotate",
        "source": "python-hotfix",
        "event": data.get("event"),
        "status": "success" if success else "non_success",
        "note": "post-verify hook executed",
    }
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
