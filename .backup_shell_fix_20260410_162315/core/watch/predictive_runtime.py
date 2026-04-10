from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PredictiveDiagnostic:
    kind: str
    severity: str
    priority: float
    confidence: float
    message: str
    line: int
    column: int
    end_line: int
    end_column: int
    code: str
    whisper: str


def _repo_root(cwd: str | None, file_path: str | None) -> Path:
    if cwd:
        return Path(cwd).expanduser().resolve()
    if file_path:
        return Path(file_path).expanduser().resolve().parent
    return Path.cwd().resolve()


def _is_local_module(top: str, repo_root: Path) -> bool:
    return (
        (repo_root / f"{top}.py").exists()
        or (repo_root / top / "__init__.py").exists()
        or (repo_root / top).is_dir()
    )


def _make_diag(
    *,
    kind: str,
    severity: str,
    priority: float,
    confidence: float,
    message: str,
    line: int,
    column: int,
    end_line: int | None = None,
    end_column: int | None = None,
    code: str | None = None,
) -> PredictiveDiagnostic:
    whisper_level = (
        "critical whisper" if priority >= 0.90 else
        "strong whisper" if priority >= 0.80 else
        "soft whisper" if priority >= 0.65 else
        "faint whisper"
    )
    return PredictiveDiagnostic(
        kind=kind,
        severity=severity,
        priority=round(float(priority), 4),
        confidence=round(float(confidence), 4),
        message=message,
        line=max(1, int(line)),
        column=max(0, int(column)),
        end_line=max(1, int(end_line if end_line is not None else line)),
        end_column=max(0, int(end_column if end_column is not None else column + 1)),
        code=code or kind,
        whisper=f"{whisper_level} — {message}",
    )


def _top_import_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        if node.names:
            return node.names[0].name.split(".")[0]
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module.split(".")[0]
    return None


def _node_pos(node: ast.AST) -> tuple[int, int, int, int]:
    line = getattr(node, "lineno", 1)
    col = getattr(node, "col_offset", 0)
    end_line = getattr(node, "end_lineno", line)
    end_col = getattr(node, "end_col_offset", col + 1)
    return line, col, end_line, end_col


def analyze_python_text(
    text: str,
    *,
    file_path: str | None = None,
    cwd: str | None = None,
    focus: str | None = None,
) -> dict[str, Any]:
    repo_root = _repo_root(cwd, file_path)
    diagnostics: list[PredictiveDiagnostic] = []

    # syntax first
    try:
        tree = ast.parse(text, filename=file_path or "<buffer>")
    except SyntaxError as e:
        diagnostics.append(
            _make_diag(
                kind="syntax-risk",
                severity="error",
                priority=0.98,
                confidence=0.98,
                message=f"syntax error at line {e.lineno}, offset {e.offset}",
                line=e.lineno or 1,
                column=max(0, (e.offset or 1) - 1),
                code="syntax-error",
            )
        )
        return {
            "file": file_path or "<buffer>",
            "focus": focus or "general_runtime",
            "diagnostics": [asdict(x) for x in diagnostics],
            "top_whisper": diagnostics[0].whisper,
        }

    # regex-level smells
    if re.search(r"(?m)^\s*import\s+\*", text):
        m = re.search(r"(?m)^\s*from\s+.+\s+import\s+\*", text)
        if m:
            diagnostics.append(
                _make_diag(
                    kind="wildcard-import-risk",
                    severity="warning",
                    priority=0.62,
                    confidence=0.84,
                    message="wildcard import namespace çakışmalarına açık",
                    line=text[:m.start()].count("\n") + 1,
                    column=0,
                    code="wildcard-import",
                )
            )

    if re.search(r"\beval\s*\(", text):
        m = re.search(r"\beval\s*\(", text)
        diagnostics.append(
            _make_diag(
                kind="eval-risk",
                severity="warning",
                priority=0.91,
                confidence=0.94,
                message="eval kullanımı yürütme ve güvenlik riski taşıyor",
                line=text[:m.start()].count("\n") + 1,
                column=0,
                code="eval-risk",
            )
        )

    if re.search(r"\bexec\s*\(", text):
        m = re.search(r"\bexec\s*\(", text)
        diagnostics.append(
            _make_diag(
                kind="exec-risk",
                severity="warning",
                priority=0.90,
                confidence=0.94,
                message="exec kullanımı yürütme akışını kırılgan hale getiriyor",
                line=text[:m.start()].count("\n") + 1,
                column=0,
                code="exec-risk",
            )
        )

    if re.search(r"subprocess\.(run|Popen)\(.*shell\s*=\s*True", text, re.S):
        m = re.search(r"subprocess\.(run|Popen)\(", text)
        diagnostics.append(
            _make_diag(
                kind="subprocess-shell-risk",
                severity="warning",
                priority=0.86,
                confidence=0.9,
                message="subprocess shell=True komut enjeksiyonu ve quoting riski taşıyor",
                line=text[:m.start()].count("\n") + 1 if m else 1,
                column=0,
                code="subprocess-shell",
            )
        )

    if "API_KEY" in text or "SECRET_KEY" in text or "TOKEN" in text:
        if re.search(r'(?m)^\s*[A-Z0-9_]*(API_KEY|SECRET|TOKEN)[A-Z0-9_]*\s*=\s*["\']', text):
            m = re.search(r'(?m)^\s*[A-Z0-9_]*(API_KEY|SECRET|TOKEN)[A-Z0-9_]*\s*=\s*["\']', text)
            diagnostics.append(
                _make_diag(
                    kind="secret-inline-risk",
                    severity="warning",
                    priority=0.88,
                    confidence=0.93,
                    message="gömülü secret/token değeri commit ve sızıntı riski taşıyor",
                    line=text[:m.start()].count("\n") + 1 if m else 1,
                    column=0,
                    code="secret-inline",
                )
            )

    has_main_guard = '__name__ == "__main__"' in text or "__name__ == '__main__'" in text

    for node in ast.walk(tree):
        line, col, end_line, end_col = _node_pos(node)

        # import risk
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            top = _top_import_name(node)
            if top:
                if isinstance(node, ast.ImportFrom) and getattr(node, "level", 0):
                    diagnostics.append(
                        _make_diag(
                            kind="relative-import-risk",
                            severity="info",
                            priority=0.55,
                            confidence=0.78,
                            message="relative import paket dışı çalıştırmada kırılabilir",
                            line=line,
                            column=col,
                            end_line=end_line,
                            end_column=end_col,
                            code="relative-import",
                        )
                    )
                if importlib.util.find_spec(top) is None and not _is_local_module(top, repo_root):
                    diagnostics.append(
                        _make_diag(
                            kind="import-risk",
                            severity="warning",
                            priority=0.78,
                            confidence=0.90,
                            message=f"`{top}` modülü bu ortamda veya repo kökünde bulunamadı",
                            line=line,
                            column=col,
                            end_line=end_line,
                            end_column=end_col,
                            code="import-missing",
                        )
                    )

        # mutable default
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = list(node.args.defaults or [])
            for d in defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    dline, dcol, de1, de2 = _node_pos(d)
                    diagnostics.append(
                        _make_diag(
                            kind="mutable-default-risk",
                            severity="warning",
                            priority=0.72,
                            confidence=0.88,
                            message=f"`{node.name}` mutable default arg kullanıyor",
                            line=dline,
                            column=dcol,
                            end_line=de1,
                            end_column=de2,
                            code="mutable-default",
                        )
                    )

        # bare except / broad except
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                diagnostics.append(
                    _make_diag(
                        kind="bare-except-risk",
                        severity="warning",
                        priority=0.76,
                        confidence=0.9,
                        message="bare except gerçek hatayı gizleyebilir",
                        line=line,
                        column=col,
                        end_line=end_line,
                        end_column=end_col,
                        code="bare-except",
                    )
                )
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                diagnostics.append(
                    _make_diag(
                        kind="broad-except-risk",
                        severity="info",
                        priority=0.63,
                        confidence=0.82,
                        message="except Exception geniş yakalama davranışı maskeleyebilir",
                        line=line,
                        column=col,
                        end_line=end_line,
                        end_column=end_col,
                        code="broad-except",
                    )
                )

        # open path risk
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                raw = node.args[0].value
                if not raw.startswith(("http://", "https://")):
                    base = Path(file_path).expanduser().resolve().parent if file_path else repo_root
                    candidate_a = (base / raw).resolve()
                    candidate_b = (repo_root / raw).resolve()
                    if not candidate_a.exists() and not candidate_b.exists():
                        diagnostics.append(
                            _make_diag(
                                kind="path-risk",
                                severity="warning",
                                priority=0.74,
                                confidence=0.87,
                                message=f"`open({raw!r})` hedefi mevcut görünmüyor",
                                line=line,
                                column=col,
                                end_line=end_line,
                                end_column=end_col,
                                code="path-open",
                            )
                        )

        # os.getenv missing default info
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os" and node.func.attr == "getenv":
                if len(node.args) == 1:
                    diagnostics.append(
                        _make_diag(
                            kind="env-default-risk",
                            severity="info",
                            priority=0.54,
                            confidence=0.76,
                            message="os.getenv default olmadan kullanılıyor; None akışı kontrol edilmeli",
                            line=line,
                            column=col,
                            end_line=end_line,
                            end_column=end_col,
                            code="env-default",
                        )
                    )

    # script main guard heuristic
    if file_path and file_path.endswith(".py") and "argparse" in text and not has_main_guard:
        diagnostics.append(
            _make_diag(
                kind="main-guard-risk",
                severity="info",
                priority=0.57,
                confidence=0.72,
                message="CLI dosyası __main__ guard olmadan çalıştırılıyor olabilir",
                line=1,
                column=0,
                code="main-guard",
            )
        )

    # de-dup
    seen: set[tuple[str, str, int]] = set()
    out: list[PredictiveDiagnostic] = []
    for d in diagnostics:
        key = (d.kind, d.message, d.line)
        if key in seen:
            continue
        seen.add(key)
        out.append(d)

    out.sort(key=lambda x: (x.priority, x.confidence), reverse=True)

    return {
        "file": file_path or "<buffer>",
        "focus": focus or "general_runtime",
        "diagnostics": [asdict(x) for x in out],
        "top_whisper": out[0].whisper if out else "",
    }


def analyze_python_file(
    file_path: str,
    *,
    cwd: str | None = None,
    focus: str | None = None,
) -> dict[str, Any]:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        diag = _make_diag(
            kind="missing-file",
            severity="error",
            priority=0.99,
            confidence=0.99,
            message="dosya bulunamadı",
            line=1,
            column=0,
            code="missing-file",
        )
        return {
            "file": str(path),
            "focus": focus or "general_runtime",
            "diagnostics": [asdict(diag)],
            "top_whisper": diag.whisper,
        }

    text = path.read_text(encoding="utf-8", errors="ignore")
    return analyze_python_text(text, file_path=str(path), cwd=cwd, focus=focus)


if __name__ == "__main__":
    import sys
    target = sys.argv[1]
    print(json.dumps(analyze_python_file(target), ensure_ascii=False, indent=2))
