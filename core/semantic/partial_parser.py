from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class PartialCrossFileAnalyzer:
    def analyze_cross_file(self, caller: Path, provider_hint: str | None = None) -> dict[str, Any] | None:
        imports = self._extract_imports(caller)
        provider_path = self._resolve_provider(caller, imports, provider_hint)

        if not provider_path or not provider_path.exists():
            return None

        api_signature = self._parse_public_api(provider_path)

        return {
            "caller_imports": imports,
            "provider_api": api_signature,
            "fault_boundary": self._find_boundary(imports, api_signature),
            "provider_path": str(provider_path),
        }

    def _extract_imports(self, file: Path) -> list[dict[str, Any]]:
        src = file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        imports: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "kind": "import",
                        "module": alias.name,
                        "asname": alias.asname,
                        "line": node.lineno,
                    })
            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "kind": "from",
                    "module": node.module,
                    "names": [x.name for x in node.names],
                    "line": node.lineno,
                    "level": node.level,
                })

        return imports

    def _resolve_provider(self, caller: Path, imports: list[dict[str, Any]], provider_hint: str | None) -> Path | None:
        root = caller.parent

        if provider_hint:
            hint = str(provider_hint)
            hint_path = Path(hint)
            if hint_path.exists():
                return hint_path
            cand = root / f"{hint.replace('.', '/')}.py"
            if cand.exists():
                return cand

        for item in imports:
            module = item.get("module")
            if not module:
                continue
            cand = root / f"{str(module).replace('.', '/')}.py"
            if cand.exists():
                return cand

        return None

    def _parse_public_api(self, file: Path) -> dict[str, Any]:
        src = file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        api = {"functions": [], "classes": []}

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                api["functions"].append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "line": node.lineno,
                })
            elif isinstance(node, ast.ClassDef):
                api["classes"].append({
                    "name": node.name,
                    "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    "line": node.lineno,
                })

        return api

    def _find_boundary(self, imports: list[dict[str, Any]], api_signature: dict[str, Any]) -> dict[str, Any]:
        imported_names = set()
        for item in imports:
            for name in item.get("names", []):
                imported_names.add(name)

        provider_functions = {f["name"] for f in api_signature.get("functions", [])}
        provider_classes = {c["name"] for c in api_signature.get("classes", [])}

        return {
            "matching_functions": sorted(imported_names & provider_functions),
            "matching_classes": sorted(imported_names & provider_classes),
        }
