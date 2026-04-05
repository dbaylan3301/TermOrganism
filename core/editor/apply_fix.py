from __future__ import annotations

import argparse
import json

from core.editor.code_actions import apply_action_to_file


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-apply-fix")
    parser.add_argument("file")
    parser.add_argument("--action-id", required=True)
    args = parser.parse_args()

    result = apply_action_to_file(args.file, args.action_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
