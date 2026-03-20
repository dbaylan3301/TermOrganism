#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/memory/retrieval.py": '''from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVENTS_PATH = Path("memory/TermOrganism/repair_events.jsonl")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def load_repair_events(limit: int | None = None) -> list[dict[str, Any]]:
    events = _read_jsonl(EVENTS_PATH)
    if limit is not None:
        return events[-limit:]
    return events


def _extract_strategy(candidate: dict[str, Any]) -> str:
    metadata = candidate.get("metadata", {}) if isinstance(candidate, dict) else {}
    if isinstance(metadata, dict):
        strategy = metadata.get("strategy")
        if isinstance(strategy, str) and strategy.strip():
            return strategy.strip()
    return ""


def _extract_kind(candidate: dict[str, Any]) -> str:
    if isinstance(candidate, dict):
        v = candidate.get("kind", "")
        return v if isinstance(v, str) else ""
    return ""


def _candidate_behavioral_success(candidate: dict[str, Any]) -> bool:
    if not isinstance(candidate, dict):
        return False
    bv = candidate.get("behavioral_verify", {})
    return isinstance(bv, dict) and bv.get("ok") is True


def historical_strategy_prior(kind: str, strategy: str, limit: int = 200) -> float:
    if not kind or not strategy:
        return 0.0

    events = load_repair_events(limit=limit)
    relevant = 0
    success = 0

    for event in events:
        best = event.get("best")
        if not isinstance(best, dict):
            best = event.get("result")

        if not isinstance(best, dict):
            continue

        best_kind = _extract_kind(best)
        best_strategy = _extract_strategy(best)

        if best_kind != kind or best_strategy != strategy:
            continue

        relevant += 1
        if _candidate_behavioral_success(best):
            success += 1

    if relevant == 0:
        return 0.0

    rate = success / relevant
    return round(0.35 * rate, 4)


def candidate_history_prior(candidate: dict[str, Any], limit: int = 200) -> float:
    if not isinstance(candidate, dict):
        return 0.0
    kind = _extract_kind(candidate)
    strategy = _extract_strategy(candidate)
    return historical_strategy_prior(kind, strategy, limit=limit)
''',

    "test_winner_only_prior.py": '''#!/usr/bin/env python3
from core.autofix import run_autofix
import json

result = run_autofix(
    error_text="Traceback (most recent call last):\\n  File \\"demo/broken_runtime.py\\", line 3, in <module>\\n    print(Path(\\"logs/app.log\\").read_text())\\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'",
    file_path="demo/broken_runtime.py",
)

print(json.dumps({
    "best_strategy": (((result.get("result") or {}).get("metadata") or {}).get("strategy")),
    "best_prior": (result.get("result") or {}).get("historical_success_prior"),
    "candidates": [
        {
            "strategy": ((c.get("metadata") or {}).get("strategy")),
            "summary": c.get("summary"),
            "historical_success_prior": c.get("historical_success_prior"),
            "repro_fix_score": c.get("repro_fix_score"),
            "regression_score": c.get("regression_score"),
            "blast_radius": c.get("blast_radius"),
        }
        for c in result.get("candidates", [])
    ]
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
