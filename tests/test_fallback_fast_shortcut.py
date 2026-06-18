from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from core.daemon.server import TermOrganismDaemon


async def run_test() -> None:
    daemon = TermOrganismDaemon(socket_path=Path("/tmp/termorganism_test.sock"))

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "fallback_case.py"
        target.write_text(
            "import definitely_missing_package_beta as dmp\nprint(dmp)\n",
            encoding="utf-8",
        )

        result = await daemon.fallback.repair(
            target,
            {"signature": "importerror:no_module_named"},
            mode="auto",
        )

        assert result["success"] is True, result
        assert result["mode"] == "fast_shortcut", result
        assert result["signature"] == "importerror:no_module_named", result
        assert result["strategy"] == "import_guard", result
        assert result["fallback_chain"] == ["hot_force_failed", "fast"], result
        assert result["verify"]["ok"] is True, result
        assert result["confidence"]["score"] >= 0.91, result

        rewritten = target.read_text(encoding="utf-8")
        assert "import definitely_missing_package_beta as dmp" in rewritten, rewritten
        assert "except ModuleNotFoundError:" in rewritten, rewritten
        assert "dmp = None" in rewritten, rewritten


def main() -> int:
    asyncio.run(run_test())
    print("OK: fallback fast shortcut")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
