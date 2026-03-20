#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/broken_runtime.py\", line 3, in <module>\n    print(Path(\"logs/app.log\").read_text())\n          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"/usr/lib/python3.13/pathlib/_local.py\", line 548, in read_text\n    return PathBase.read_text(self, encoding, errors, newline)\n  File \"/usr/lib/python3.13/pathlib/_abc.py\", line 632, in read_text\n    with self.open(mode='r', encoding=encoding, errors=errors, newline=newline) as f:\n  File \"/usr/lib/python3.13/pathlib/_local.py\", line 539, in open\n    return io.open(self, mode, buffering, encoding, errors, newline)\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
    file_path="demo/broken_runtime.py",
)

loc = ((result.get("semantic") or {}).get("localization") or {})
print(json.dumps({
    "top": loc.get("top"),
    "items": loc.get("items"),
}, ensure_ascii=False, indent=2))
