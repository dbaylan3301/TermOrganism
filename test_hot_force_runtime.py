from __future__ import annotations

from pathlib import Path
import tempfile

from core.orchestrator_hot_force import HotCacheForcePath


def main() -> int:
    engine = HotCacheForcePath()

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "broken_runtime.py"
        target.write_text('print(open("logs/app.log").read())\n', encoding="utf-8")

        result = engine.repair(
            target,
            {"signature": "filenotfounderror:open:runtime"},
        )

        assert result["success"] is True, result
        assert result["mode"] == "hot_force_path", result
        assert result["signature"] == "filenotfounderror:open:runtime", result
        assert result["verify"]["ok"] is True, result
        assert result["confidence"]["score"] >= 0.97, result

        rewritten = target.read_text(encoding="utf-8")
        assert 'log_path = Path("logs/app.log")' in rewritten, rewritten
        assert 'print("")' in rewritten, rewritten

    print("OK: hot_force runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
