#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"demo/broken_runtime.py\", line 3, in <module>\n    print(Path(\"logs/app.log\").read_text())\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "candidate_count": result.get("candidate_count"),
    "best_summary": (result.get("result") or {}).get("summary"),
    "best_hypothesis": (result.get("result") or {}).get("hypothesis"),
    "candidates": [
        {
            "summary": c.get("summary"),
            "hypothesis": c.get("hypothesis"),
            "repro_fix_score": c.get("repro_fix_score"),
            "regression_score": c.get("regression_score"),
            "blast_radius": c.get("blast_radius"),
        }
        for c in result.get("candidates", [])
    ]
}, ensure_ascii=False, indent=2))
