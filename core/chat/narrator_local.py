from __future__ import annotations

import argparse
from core.llm.text_variation import vary_narration_text


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-narrate-local")
    parser.add_argument("text", nargs="+")
    args = parser.parse_args()

    base = " ".join(args.text).strip()
    out = vary_narration_text(
        base,
        context={
            "mode": "local_narration",
            "style": "short_professional",
        },
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
