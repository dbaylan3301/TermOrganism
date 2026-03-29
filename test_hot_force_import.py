from __future__ import annotations

from pathlib import Path
import tempfile

from core.orchestrator_hot_force import HotCacheForcePath


def main() -> int:
    engine = HotCacheForcePath()

    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "broken_import.py"
        target.write_text("import definitely_missing_package_12345\n", encoding="utf-8")

        result = engine.repair(
            target,
            {"signature": "importerror:no_module_named"},
        )

        assert result["success"] is True, result
        assert result["mode"] == "hot_force_path", result
        assert result["signature"] == "importerror:no_module_named", result
        assert result["strategy"] == "import_guard", result
        assert result["verify"]["ok"] is True, result
        assert result["confidence"]["score"] >= 0.95, result

        rewritten = target.read_text(encoding="utf-8")
        assert "except ModuleNotFoundError:" in rewritten, rewritten
        assert "definitely_missing_package_12345 = None" in rewritten, rewritten

    print("OK: hot_force import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
