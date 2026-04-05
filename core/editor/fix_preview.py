from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.editor.code_actions import build_code_actions_for_text


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-fix-preview")
    parser.add_argument("file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    text = path.read_text(encoding="utf-8", errors="ignore")
    payload = build_code_actions_for_text(text, file_path=str(path))

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"[preview] {path}")
    for idx, action in enumerate(payload["actions"], start=1):
        mode = "apply" if action["auto_apply"] else "preview"
        print(f"{idx}. [{mode}] {action['title']} ({action['diagnostic_kind']}) id={action['action_id']}")
        print(f"   {action['message']}")
        if action["preview"]:
            print(f"   → {action['preview'][:220]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
