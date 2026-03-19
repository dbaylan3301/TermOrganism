#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any


ROOT = Path.cwd()

REQUIRED_FILES = [
    "core/__init__.py",
    "core/autofix.py",
    "core/engine/__init__.py",
    "core/engine/context_builder.py",
    "core/engine/orchestrator.py",
    "core/engine/ranker.py",
    "core/engine/router.py",
    "core/experts/__init__.py",
    "core/experts/base.py",
    "core/experts/dependency.py",
    "core/experts/llm_fallback.py",
    "core/experts/memory_retrieval.py",
    "core/experts/python_syntax.py",
    "core/experts/shell_runtime.py",
    "core/memory/__init__.py",
    "core/memory/event_store.py",
    "core/memory/retrieval.py",
    "core/memory/stats.py",
    "core/models/__init__.py",
    "core/models/schemas.py",
    "core/util/__init__.py",
    "core/util/diffing.py",
    "core/util/fingerprints.py",
    "core/util/logging.py",
    "core/verify/__init__.py",
    "core/verify/python_verify.py",
    "core/verify/sandbox.py",
    "memory/TermOrganism/repair_events.jsonl",
]

REQUIRED_IMPORTS = [
    "core.autofix",
    "core.engine.context_builder",
    "core.engine.orchestrator",
    "core.engine.ranker",
    "core.engine.router",
    "core.experts.base",
    "core.experts.dependency",
    "core.experts.llm_fallback",
    "core.experts.memory_retrieval",
    "core.experts.python_syntax",
    "core.experts.shell_runtime",
    "core.memory.event_store",
    "core.memory.retrieval",
    "core.memory.stats",
    "core.models.schemas",
    "core.util.diffing",
    "core.util.fingerprints",
    "core.util.logging",
    "core.verify.python_verify",
    "core.verify.sandbox",
]

AUTOFIX_EXPECTED_HINTS = {
    "engine_refs": [
        "context_builder",
        "orchestrator",
        "ranker",
        "router",
    ],
    "verify_refs": [
        "python_verify",
        "sandbox",
        "verify",
    ],
    "memory_refs": [
        "event_store",
        "repair_events",
        "retrieval",
        "stats",
    ],
}

EXPERT_MODULES = [
    "dependency",
    "llm_fallback",
    "memory_retrieval",
    "python_syntax",
    "shell_runtime",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def exists_check(root: Path) -> List[CheckResult]:
    results = []
    for rel in REQUIRED_FILES:
        p = root / rel
        results.append(
            CheckResult(
                name=f"exists:{rel}",
                ok=p.exists(),
                details=str(p),
            )
        )
    return results


def import_check() -> List[CheckResult]:
    results = []
    for mod in REQUIRED_IMPORTS:
        try:
            importlib.import_module(mod)
            results.append(CheckResult(f"import:{mod}", True, "ok"))
        except Exception as e:
            results.append(CheckResult(f"import:{mod}", False, f"{type(e).__name__}: {e}"))
    return results


def parse_python(path: Path) -> CheckResult:
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        return CheckResult(f"syntax:{path.relative_to(ROOT)}", True, "AST parse ok")
    except Exception as e:
        return CheckResult(f"syntax:{path.relative_to(ROOT)}", False, f"{type(e).__name__}: {e}")


def syntax_check(root: Path) -> List[CheckResult]:
    results = []
    for rel in REQUIRED_FILES:
        if rel.endswith(".py"):
            p = root / rel
            if p.exists():
                results.append(parse_python(p))
    return results


def autofix_linkage_check(root: Path) -> List[CheckResult]:
    results = []
    autofix = root / "core/autofix.py"
    if not autofix.exists():
        return [CheckResult("autofix_linkage", False, "core/autofix.py yok")]

    text = autofix.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()

    for key, hints in AUTOFIX_EXPECTED_HINTS.items():
        found = [h for h in hints if h.lower() in lower]
        results.append(
            CheckResult(
                name=f"autofix:{key}",
                ok=len(found) > 0,
                details=f"bulunan={found}" if found else f"hiçbiri yok: {hints}",
            )
        )

    expert_found = [m for m in EXPERT_MODULES if m in lower]
    results.append(
        CheckResult(
            name="autofix:expert_refs",
            ok=len(expert_found) > 0,
            details=f"bulunan={expert_found}" if expert_found else "expert referansı görünmedi",
        )
    )

    return results


def event_store_check(root: Path) -> List[CheckResult]:
    results = []
    path = root / "memory/TermOrganism/repair_events.jsonl"
    if not path.exists():
        return [CheckResult("event_store:file", False, "repair_events.jsonl yok")]

    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            results.append(CheckResult("event_store:readable", True, "dosya var, şimdilik boş"))
            return results

        lines = text.splitlines()
        bad = 0
        for line in lines[-10:]:
            try:
                json.loads(line)
            except Exception:
                bad += 1

        results.append(
            CheckResult(
                "event_store:jsonl_tail",
                ok=(bad == 0),
                details=f"son {min(10, len(lines))} satır kontrol edildi, hatalı={bad}",
            )
        )
    except Exception as e:
        results.append(CheckResult("event_store:readable", False, f"{type(e).__name__}: {e}"))

    return results


def orchestrator_semantic_check(root: Path) -> List[CheckResult]:
    results = []
    targets = {
        "core/engine/router.py": ["route", "expert", "select"],
        "core/engine/ranker.py": ["rank", "score", "candidate"],
        "core/engine/orchestrator.py": ["orchestr", "expert", "verify", "rank"],
        "core/engine/context_builder.py": ["context", "traceback", "stderr", "stdout"],
    }

    for rel, hints in targets.items():
        p = root / rel
        if not p.exists():
            results.append(CheckResult(f"semantic:{rel}", False, "dosya yok"))
            continue

        txt = p.read_text(encoding="utf-8", errors="replace").lower()
        found = [h for h in hints if h in txt]
        results.append(
            CheckResult(
                f"semantic:{rel}",
                ok=len(found) >= max(1, len(hints) // 2),
                details=f"bulunan={found}, beklenen={hints}",
            )
        )
    return results


def score(results: List[CheckResult]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    pct = round((passed / total) * 100, 2) if total else 0.0

    if pct >= 90:
        verdict = "Büyük ölçüde devrede"
    elif pct >= 70:
        verdict = "Kısmen devrede, bazı bağlantılar eksik"
    elif pct >= 40:
        verdict = "İskelet kurulmuş ama pipeline eksik"
    else:
        verdict = "Henüz devrede değil"

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "score_percent": pct,
        "verdict": verdict,
    }


def print_report(results: List[CheckResult]) -> None:
    summary = score(results)

    print("=" * 72)
    print("TermOrganism MoE-style Repair Orchestrator Smoke Test")
    print("=" * 72)
    print(f"Toplam check : {summary['total']}")
    print(f"Geçen        : {summary['passed']}")
    print(f"Kalan        : {summary['failed']}")
    print(f"Skor         : %{summary['score_percent']}")
    print(f"Durum        : {summary['verdict']}")
    print("-" * 72)

    failed = [r for r in results if not r.ok]
    passed = [r for r in results if r.ok]

    if failed:
        print("Başarısız kontroller:")
        for r in failed:
            print(f"  [FAIL] {r.name} -> {r.details}")
        print("-" * 72)

    print("Özet geçen kontroller:")
    for r in passed[:20]:
        print(f"  [OK]   {r.name} -> {r.details}")

    if len(passed) > 20:
        print(f"  ... ve {len(passed) - 20} ek başarılı kontrol daha var.")
    print("-" * 72)

    # Pipeline-specific verdict
    critical = {
        "core/autofix.py": (ROOT / "core/autofix.py").exists(),
        "core/engine/orchestrator.py": (ROOT / "core/engine/orchestrator.py").exists(),
        "core/engine/router.py": (ROOT / "core/engine/router.py").exists(),
        "core/engine/ranker.py": (ROOT / "core/engine/ranker.py").exists(),
        "core/verify/python_verify.py": (ROOT / "core/verify/python_verify.py").exists(),
        "memory/TermOrganism/repair_events.jsonl": (ROOT / "memory/TermOrganism/repair_events.jsonl").exists(),
    }

    print("Kritik pipeline bileşenleri:")
    for name, ok in critical.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    print("=" * 72)


def main() -> int:
    results: List[CheckResult] = []
    results.extend(exists_check(ROOT))
    results.extend(syntax_check(ROOT))
    results.extend(import_check())
    results.extend(autofix_linkage_check(ROOT))
    results.extend(event_store_check(ROOT))
    results.extend(orchestrator_semantic_check(ROOT))

    print_report(results)

    summary = score(results)
    return 0 if summary["score_percent"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
