from __future__ import annotations

import json
import subprocess
from pathlib import Path
from core.hooks.events import HookEvent


def run_hook(command: str | Path, event: HookEvent, timeout_sec: int = 10) -> dict:
    proc = subprocess.run(
        [str(command)],
        input=json.dumps({
            "event": event.name,
            "payload": event.payload,
            "metadata": event.metadata,
        }),
        text=True,
        capture_output=True,
        timeout=timeout_sec,
        check=False,
    )
    if not proc.stdout.strip():
        return {"ok": proc.returncode == 0, "action": "noop"}
    return json.loads(proc.stdout)
