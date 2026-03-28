from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class JavaScriptExpert:
    """
    JavaScript/TypeScript repair expert.
    Safe additive version:
    - tree-sitter optional
    - regex fallback if parser deps are unavailable
    - returns existing candidate schema used by planner/autofix
    """

    JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def __init__(self):
        self.patterns = self._load_patterns()
        self._parser = None
        self._language = None
        self._init_parser()

    def _init_parser(self):
        try:
            import tree_sitter_javascript as tsjs
            from tree_sitter import Language, Parser
            self._language = Language(tsjs.language())
            self._parser = Parser(self._language)
        except Exception:
            self._parser = None
            self._language = None

    def supports(self, file_path: str | None) -> bool:
        if not file_path:
            return False
        return Path(str(file_path)).suffix.lower() in self.JS_EXTS

    def _load_patterns(self) -> dict[str, dict[str, Any]]:
        return {
            "import_error": {
                "detect": self._detect_import_error,
                "repair": self._repair_import,
                "confidence": 0.90,
            },
            "undefined_variable": {
                "detect": self._detect_undefined,
                "repair": self._repair_undefined,
                "confidence": 0.85,
            },
            "syntax_error": {
                "detect": self._detect_syntax,
                "repair": self._repair_syntax,
                "confidence": 0.95,
            },
            "async_await_error": {
                "detect": self._detect_async_error,
                "repair": self._repair_async,
                "confidence": 0.80,
            },
        }

    def propose(self, *, error_text: str, file_path: str | None = None) -> list[dict[str, Any]]:
        if not self.supports(file_path):
            return []

        path = Path(str(file_path))
        try:
            code = path.read_text(encoding="utf-8")
        except Exception:
            return []

        context = self._build_error_context(error_text, path)
        tree = self._parse_tree(code)
        error_line = context.get("line", 0)
        error_node = self._find_node_at_line(tree, error_line, code)

        repairs: list[dict[str, Any]] = []
        for pattern_name, pattern in self.patterns.items():
            try:
                if pattern["detect"](error_node, context):
                    repair = pattern["repair"](error_node, code, path, context)
                    candidate_code = str(repair.get("code") or "")
                    summary = str(repair.get("description") or pattern_name)

                    repairs.append({
                        "expert": "javascript",
                        "kind": f"js_{pattern_name}",
                        "summary": summary,
                        "description": summary,
                        "confidence": float(pattern["confidence"]),
                        "candidate_code": candidate_code,
                        "target_file": str(path),
                        "file_path_hint": str(path),
                        "metadata": {
                            "language": "javascript",
                            "alternatives": repair.get("alternatives", []),
                            "auto_fixable": bool(repair.get("auto_fixable", False)),
                            "location": {
                                "start_line": int(error_node.get("start_line", error_line)),
                                "end_line": int(error_node.get("end_line", error_line)),
                            },
                        },
                    })
            except Exception:
                continue

        repairs.sort(key=lambda x: (-float(x.get("confidence", 0.0) or 0.0), str(x.get("kind") or "")))
        return repairs

    def _build_error_context(self, error_text: str, path: Path) -> dict[str, Any]:
        msg = error_text or ""
        line = 0

        m = re.search(rf'{re.escape(path.name)}[:(](\d+)', msg)
        if not m:
            m = re.search(r'line (\d+)', msg)
        if m:
            try:
                line = max(0, int(m.group(1)) - 1)
            except Exception:
                line = 0

        err_type = "UnknownError"
        m2 = re.search(r'([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))', msg)
        if m2:
            err_type = m2.group(1)

        return {
            "message": msg,
            "line": line,
            "type": err_type,
            "target_file": str(path),
        }

    def _parse_tree(self, code: str):
        if self._parser is None:
            return None
        try:
            return self._parser.parse(code.encode("utf-8"))
        except Exception:
            return None

    def _detect_import_error(self, node, context) -> bool:
        error_msg = (context.get("message") or "").lower()
        return any(x in error_msg for x in [
            "cannot find module",
            "module not found",
            "require is not defined",
            "import error",
            "err_module_not_found",
        ])

    def _repair_import(self, node, code: str, file_path: Path, context: dict) -> dict[str, Any]:
        lines = code.splitlines()
        line_no = min(max(0, int(context.get("line", 0))), max(0, len(lines) - 1)) if lines else 0
        import_line = lines[line_no] if lines else ""

        fixes: list[str] = []
        modified = import_line

        modified = re.sub(r'(from\s+[\'"]\./[^\'".]+)([\'"])', r'\1.js\2', modified)
        modified = re.sub(r'(require\([\'"]\./[^\'".]+)([\'"]\))', r'\1.js\2', modified)
        fixes.append(modified if modified else import_line)

        req_match = re.search(r'const\s+(\w+)\s*=\s*require\(([\'"].+?[\'"])\)', import_line)
        if req_match:
            fixes.append(f'import {req_match.group(1)} from {req_match.group(2)};')

        pkg_match = re.search(r"Cannot find module ['\"]([^'\"]+)['\"]", context.get("message") or "")
        if pkg_match:
            fixes.append(import_line + f" // TODO: npm install {pkg_match.group(1)}")

        chosen = fixes[0] if fixes else import_line
        if lines:
            lines[line_no] = chosen
            new_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
        else:
            new_code = chosen + "\n"

        return {
            "description": "Fix JavaScript module resolution or import form",
            "code": new_code,
            "alternatives": fixes,
        }

    def _detect_undefined(self, node, context) -> bool:
        error_msg = context.get("message", "")
        return "is not defined" in error_msg or "ReferenceError" in error_msg

    def _repair_undefined(self, node, code: str, file_path: Path, context: dict) -> dict[str, Any]:
        msg = context.get("message", "")
        m = re.search(r'([A-Za-z_$][A-Za-z0-9_$]*) is not defined', msg)
        var_name = m.group(1) if m else (node.get("text") or "missingSymbol")

        alternatives = [
            f"const {var_name} = null;",
            f"let {var_name};",
            f"// FIXME: {var_name} not defined",
        ]

        new_code = alternatives[0] + "\n" + code
        return {
            "description": f"Define missing JavaScript variable '{var_name}'",
            "code": new_code,
            "alternatives": alternatives,
        }

    def _detect_syntax(self, node, context) -> bool:
        t = str(context.get("type") or "")
        msg = (context.get("message") or "").lower()
        return t == "SyntaxError" or "syntaxerror" in msg or "unexpected token" in msg

    def _repair_syntax(self, node, code: str, file_path: Path, context: dict) -> dict[str, Any]:
        lines = code.splitlines()
        line_no = min(max(0, int(context.get("line", 0))), max(0, len(lines) - 1)) if lines else 0

        alternatives: list[str] = []

        if lines:
            line = lines[line_no]
            if line and not line.strip().endswith((";", "{", "}", ",")):
                fixed_lines = list(lines)
                fixed_lines[line_no] = line.rstrip() + ";"
                alternatives.append("\n".join(fixed_lines) + ("\n" if code.endswith("\n") else ""))

        alternatives.append(code)
        return {
            "description": "Prepare JavaScript syntax fix candidate",
            "code": alternatives[0],
            "alternatives": alternatives,
            "auto_fixable": True,
        }

    def _detect_async_error(self, node, context) -> bool:
        error_msg = (context.get("message") or "").lower()
        return any(x in error_msg for x in [
            "await is only valid in async function",
            "unhandledpromiserejection",
            "promise rejection",
        ])

    def _repair_async(self, node, code: str, file_path: Path, context: dict) -> dict[str, Any]:
        lines = code.splitlines()
        line_no = min(max(0, int(context.get("line", 0))), max(0, len(lines) - 1)) if lines else 0

        func_start = self._find_function_start(lines, line_no)
        alternatives: list[str] = []

        if 0 <= func_start < len(lines):
            candidate = list(lines)
            if not candidate[func_start].lstrip().startswith("async "):
                candidate[func_start] = "async " + candidate[func_start]
            alternatives.append("\n".join(candidate) + ("\n" if code.endswith("\n") else ""))

        alternatives.append(f"Promise.resolve().then(async () => {{\n{code}\n}})")
        alternatives.append(f"try {{\n{code}\n}} catch (e) {{ console.error(e); }}")

        return {
            "description": "Add async keyword or wrap Promise handling",
            "code": alternatives[0],
            "alternatives": alternatives,
        }

    def _find_node_at_line(self, tree, line: int, code: str) -> dict[str, Any]:
        lines = code.splitlines()
        text = lines[line] if lines and 0 <= line < len(lines) else ""
        if tree is None:
            return {
                "start_line": line,
                "end_line": line,
                "text": text,
                "type": "line",
            }

        return {
            "start_line": line,
            "end_line": line,
            "text": text,
            "type": "line",
        }

    def _find_function_start(self, lines: list[str], line_no: int) -> int:
        for i in range(line_no, -1, -1):
            line = lines[i].strip()
            if (
                line.startswith("function ")
                or "=>" in line
                or line.startswith("const ")
                or line.startswith("let ")
                or line.startswith("var ")
            ):
                return i
        return line_no
