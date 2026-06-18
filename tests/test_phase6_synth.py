#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"demo/broken_runtime.py\", line 3, in <module>\n    print(Path(\"logs/app.log\").read_text())\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "best_synth_score": (result.get("result") or {}).get("synth_test_score"),
    "best_synthesized_tests": result.get("synthesized_tests"),
    "candidates": [
        {
            "strategy": ((c.get("metadata") or {}).get("strategy")),
            "summary": c.get("summary"),
            "synth_test_score": c.get("synth_test_score"),
            "synth_ok": ((c.get("synthesized_tests") or {}).get("ok")),
        }
        for c in result.get("candidates", [])
    ]
}, ensure_ascii=False, indent=2))
