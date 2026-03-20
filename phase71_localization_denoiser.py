#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/semantic/fault_localizer.py": '''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re
import sysconfig


@dataclass
class Suspicion:
    file_path: str
    line_no: int | None
    symbol: str | None
    reason: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TRACE_FILE_RE = re.compile(r'File "([^"]+)", line ([0-9]+)')
IMPORT_RE = re.compile(r'^(?:from\\s+([a-zA-Z0-9_\\.]+)\\s+import|import\\s+([a-zA-Z0-9_\\.]+))', re.MULTILINE)

_STDLIB_PATHS = {
    Path(sysconfig.get_paths().get("stdlib", "")).resolve(),
    Path(sysconfig.get_paths().get("platstdlib", "")).resolve(),
}


def _safe_resolve(p: str | Path) -> Path:
    try:
        return Path(p).resolve()
    except Exception:
        return Path(str(p))


def _guess_project_root(file_path: str | None) -> Path | None:
    if not file_path:
        return None

    cur = _safe_resolve(file_path)
    if cur.is_file():
        cur = cur.parent

    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}
    for base in [cur, *cur.parents]:
        if any((base / m).exists() for m in markers):
            return base
    return cur


def _is_under(child: Path, parent: Path | None) -> bool:
    if parent is None:
        return False
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


def _is_stdlib(path: Path) -> bool:
    return any(_is_under(path, base) for base in _STDLIB_PATHS if str(base) != ".")


def _is_site_packages(path: Path) -> bool:
    s = str(path)
    return "site-packages" in s or "dist-packages" in s


def _repair_weight(item: Suspicion, target_file: str | None, project_root: Path | None) -> float:
    score = float(item.score)

    fp = _safe_resolve(item.file_path)
    target = _safe_resolve(target_file) if target_file else None

    if target and fp == target:
        score += 0.30

    if project_root and _is_under(fp, project_root):
        score += 0.18

    if item.reason == "import-neighbor candidate module":
        score += 0.10

    if _is_site_packages(fp):
        score -= 0.18

    if _is_stdlib(fp):
        score -= 0.30

    return round(score, 4)


def _collect_trace_suspicions(error_text: str) -> list[Suspicion]:
    out: list[Suspicion] = []
    for m in TRACE_FILE_RE.finditer(error_text or ""):
        out.append(
            Suspicion(
                file_path=m.group(1),
                line_no=int(m.group(2)),
                symbol=None,
                reason="traceback-localized frame",
                score=0.88,
            )
        )
    return out


def _collect_signature_suspicions(error_text: str, file_path: str | None) -> list[Suspicion]:
    text = error_text or ""
    path = file_path or "<unknown>"
    out: list[Suspicion] = []

    lowered = text.lower()

    if "modulenotfounderror" in lowered or "no module named" in lowered:
        out.append(Suspicion(path, 1, None, "dependency/import failure at module import boundary", 0.84))

    if "filenotfounderror" in lowered or "no such file or directory" in lowered:
        out.append(Suspicion(path, None, None, "runtime path/file access failure", 0.82))

    if "syntaxerror" in lowered or "indentationerror" in lowered:
        out.append(Suspicion(path, None, None, "syntax failure in target module", 0.86))

    if "command not found" in lowered:
        out.append(Suspicion(path, None, None, "shell executable resolution failure", 0.76))

    if "permission denied" in lowered:
        out.append(Suspicion(path, None, None, "permission boundary failure", 0.73))

    if not out:
        out.append(Suspicion(path, None, None, "generic localized failure", 0.50))

    return out


def _collect_import_neighbors(file_path: str | None) -> list[Suspicion]:
    if not file_path:
        return []

    p = Path(file_path)
    if not p.exists() or p.suffix != ".py":
        return []

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    out: list[Suspicion] = []
    seen: set[str] = set()

    for m in IMPORT_RE.finditer(text):
        mod = m.group(1) or m.group(2) or ""
        base = mod.split(".")[0].strip()
        if not base or base in seen:
            continue
        seen.add(base)

        neighbor = p.parent / f"{base}.py"
        if neighbor.exists():
            out.append(
                Suspicion(
                    file_path=str(neighbor.resolve()),
                    line_no=None,
                    symbol=base,
                    reason="import-neighbor candidate module",
                    score=0.42,
                )
            )

    return out


def localize_fault(error_text: str, file_path: str | None = None) -> list[Suspicion]:
    items: list[Suspicion] = []
    items.extend(_collect_trace_suspicions(error_text))
    items.extend(_collect_signature_suspicions(error_text, file_path))
    items.extend(_collect_import_neighbors(file_path))

    project_root = _guess_project_root(file_path)

    best: dict[tuple[str, int | None, str | None, str], Suspicion] = {}
    for item in items:
        key = (item.file_path, item.line_no, item.symbol, item.reason)
        weighted = Suspicion(
            file_path=item.file_path,
            line_no=item.line_no,
            symbol=item.symbol,
            reason=item.reason,
            score=_repair_weight(item, file_path, project_root),
        )
        if key not in best or weighted.score > best[key].score:
            best[key] = weighted

    return sorted(best.values(), key=lambda x: x.score, reverse=True)


def summarize_suspicions(items: list[Suspicion]) -> dict[str, Any]:
    arr = [x.to_dict() if hasattr(x, "to_dict") else x for x in items]
    return {
        "count": len(arr),
        "top": arr[0] if arr else None,
        "items": arr,
    }
''',

    "test_phase71_denoiser.py": '''#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\\n  File \\"/root/TermOrganismGitFork/demo/broken_runtime.py\\", line 3, in <module>\\n    print(Path(\\"logs/app.log\\").read_text())\\n          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\\n  File \\"/usr/lib/python3.13/pathlib/_local.py\\", line 548, in read_text\\n    return PathBase.read_text(self, encoding, errors, newline)\\n  File \\"/usr/lib/python3.13/pathlib/_abc.py\\", line 632, in read_text\\n    with self.open(mode='r', encoding=encoding, errors=errors, newline=newline) as f:\\n  File \\"/usr/lib/python3.13/pathlib/_local.py\\", line 539, in open\\n    return io.open(self, mode, buffering, encoding, errors, newline)\\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\\n",
    file_path="demo/broken_runtime.py",
)

loc = ((result.get("semantic") or {}).get("localization") or {})
print(json.dumps({
    "top": loc.get("top"),
    "items": loc.get("items"),
}, ensure_ascii=False, indent=2))
''',
}


def backup_and_write(rel_path: str, content: str) -> None:
    path = ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        print(f"[BACKUP] {rel_path} -> {backup.relative_to(ROOT)}")
    path.write_text(content, encoding="utf-8")
    print(f"[WRITE]  {rel_path}")


def main() -> int:
    for rel_path, content in PATCHES.items():
        backup_and_write(rel_path, content)
    print("\\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
