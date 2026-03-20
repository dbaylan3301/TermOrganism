#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"demo/broken_runtime.py\", line 3, in <module>\n    print(Path(\"logs/app.log\").read_text())\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "sandbox": result.get("sandbox"),
    "candidate_sandboxes": [
        {
            "strategy": ((c.get("metadata") or {}).get("strategy")),
            "sandbox_ok": ((c.get("sandbox") or {}).get("ok")),
            "sandbox_reason": ((c.get("sandbox") or {}).get("reason")),
        }
        for c in result.get("candidates", [])
    ]
}, ensure_ascii=False, indent=2))
