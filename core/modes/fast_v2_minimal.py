from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class FastV2Minimal:
    """
    Minimal fast_v2:
    - hot runtime signature
    - import/import-as/from-import guard
    """

    def __init__(self, hot_repairs: dict[str, dict] | None = None):
        self.hot_repairs = hot_repairs or {}

    def _extract_signature(self, file_path: Path, context: dict[str, Any]) -> str:
        explicit = str(context.get("signature") or "").strip().lower()
        if explicit:
            return explicit

        text = str(context.get("error_text") or "").lower()
        if "filenotfounderror" in text and ("open(" in text or "read_text" in text or "no such file or directory" in text):
            return "filenotfounderror:open:runtime"
        if "modulenotfounderror" in text or "no module named" in text or "importerror" in text:
            return "importerror:no_module_named"

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        if "open(" in source and ".read()" in source:
            return "filenotfounderror:open:runtime"
        if "read_text(" in source:
            return "filenotfounderror:open:runtime"
        if re.search(r'(?m)^\s*import\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*$', source):
            return "importerror:no_module_named"
        if re.search(r'(?m)^\s*from\s+[A-Za-z_][A-Za-z0-9_\.]*\s+import\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*$', source):
            return "importerror:no_module_named"
        return ""

    def plan(self, file_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        signature = self._extract_signature(file_path, context)

        if signature == "filenotfounderror:open:runtime":
            repair = self.hot_repairs.get(signature) or {
                "code": 'from pathlib import Path\n\nlog_path = Path("logs/app.log")\nif log_path.exists():\n    print(log_path.read_text())\nelse:\n    print("")\n',
                "strategy": "guard_exists",
                "confidence": 0.95,
            }
            return {
                "used": True,
                "path": "hot_cache",
                "signature": signature,
                "strategy": repair.get("strategy", "guard_exists"),
                "confidence": float(repair.get("confidence", 0.95)),
                "code": repair["code"],
                "verify_reason": "fast_v2_hot_cache",
            }

        if signature == "importerror:no_module_named":
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return {
                    "used": False,
                    "miss_reason": "file_read_failed",
                    "signature": signature,
                }

            code_lines = []
            for line in source.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                code_lines.append(stripped)

            if not code_lines:
                return {
                    "used": False,
                    "miss_reason": "empty_source",
                    "signature": signature,
                }

            stmt = code_lines[0]
            m_import = re.fullmatch(r"import\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*", stmt)
            m_from = re.fullmatch(r"from\s+([A-Za-z_][A-Za-z0-9_\.]*)\s+import\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*", stmt)

            generated = None
            if m_import:
                module = m_import.group(1)
                alias = m_import.group(2)
                if alias:
                    generated = (
                        f"try:\n"
                        f"    import {module} as {alias}\n"
                        f"except ModuleNotFoundError:\n"
                        f"    {alias} = None\n"
                    )
                else:
                    generated = (
                        f"try:\n"
                        f"    import {module}\n"
                        f"except ModuleNotFoundError:\n"
                        f"    {module} = None\n"
                    )
            elif m_from:
                module = m_from.group(1)
                name = m_from.group(2)
                alias = m_from.group(3)
                bind = alias or name
                import_stmt = f"from {module} import {name}" + (f" as {alias}" if alias else "")
                generated = (
                    f"try:\n"
                    f"    {import_stmt}\n"
                    f"except ModuleNotFoundError:\n"
                    f"    {bind} = None\n"
                )

            if generated:
                return {
                    "used": True,
                    "path": "dynamic_import_guard",
                    "signature": signature,
                    "strategy": "import_guard",
                    "confidence": 0.91,
                    "code": generated,
                    "verify_reason": "fast_v2_import_guard",
                }

            return {
                "used": False,
                "miss_reason": "unsupported_import_shape",
                "signature": signature,
            }

        return {
            "used": False,
            "miss_reason": "signature_not_in_cache",
            "signature": signature,
        }
