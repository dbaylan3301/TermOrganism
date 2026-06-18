#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"demo/broken_runtime.py\", line 3, in <module>\n    print(Path(\"logs/app.log\").read_text())\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_summary": (result.get("result") or {}).get("summary"),
    "top_localization": ((result.get("semantic") or {}).get("localization") or {}).get("top"),
    "import_neighbors": [
        x for x in (((result.get("semantic") or {}).get("localization") or {}).get("items") or [])
        if x.get("reason") == "import-neighbor candidate module"
    ],
    "sandbox": result.get("sandbox"),
    "synthesized_tests": result.get("synthesized_tests"),
}, ensure_ascii=False, indent=2))
