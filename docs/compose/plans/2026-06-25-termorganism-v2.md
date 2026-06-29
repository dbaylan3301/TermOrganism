# TermOrganism v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor TermOrganism from a monolithic architecture to a modular, plugin-extensible, well-tested, CI/CD-ready v2 release.

**Architecture:** Split the 1936-line `core/autofix.py` into focused modules under `core/repair/`. Introduce a plugin API that allows external modules to register experts and tools. Expand test coverage from 38 to ~70+ tests. Add GitHub Actions CI/CD. Clean up legacy migration scripts.

**Tech Stack:** Python 3.10+, pytest, ruff, mypy, GitHub Actions

---

## File Structure

### New files to create:
```
core/repair/
├── __init__.py          # Public API: repair()
├── engine.py            # Main repair orchestration loop
├── candidates.py        # Expert candidate generation
├── planner.py           # Plan building and ranking
├── verify.py            # Sandbox verification helpers
├── hot_cache.py         # Hot cache boost logic
├── events.py            # ThoughtEvent emission, EventStoreAdapter
└── utils.py             # _force_plan_target_to_file, _resolve_semantic_target

core/plugins/
├── __init__.py
├── base.py              # Plugin ABC
├── registry.py          # Plugin loading and management
└── builtin/
    └── python_hotfix.py # Migrated from plugins/builtin/python-hotfix

tests/
├── test_repair_engine.py
├── test_repair_candidates.py
├── test_repair_planner.py
├── test_repair_verify.py
├── test_repair_hot_cache.py
├── test_repair_utils.py
├── test_plugin_api.py
├── test_plugin_registry.py
├── test_expert_file_runtime.py
├── test_expert_python_syntax.py
├── test_expert_dependency.py
├── test_expert_shell_runtime.py
├── test_expert_memory_retrieval.py
├── test_expert_llm_fallback.py
├── test_tool_bash.py
├── test_tool_file_read.py
├── test_tool_file_write.py
├── test_tool_edit.py
├── test_tool_glob.py
├── test_tool_grep.py
├── test_tool_git.py
├── test_tool_task.py
├── test_tool_question.py
├── test_tool_memory.py

.github/
└── workflows/
    └── ci.yml           # lint, test, typecheck

docs/
└── v2-changelog.md
```

### Files to modify:
- `core/autofix.py` — keep as backward-compat shim, import from `core.repair`
- `pyproject.toml` — version bump, add entry points, add dev deps
- `README.md` — update with v2 features
- `core/mimo/tools/registry.py` — add plugin tool registration support

### Files to delete:
- `restructure_termorganism.sh`
- `relocate_from_core.sh`

---

## Task 1: Create core/repair/ package structure

**Covers:** S1 (autofix.py split)

**Files:**
- Create: `core/repair/__init__.py`
- Create: `core/repair/utils.py`
- Create: `core/repair/events.py`
- Create: `core/repair/hot_cache.py`

- [ ] **Step 1: Create core/repair/__init__.py**

```python
from __future__ import annotations

from .engine import repair

__all__ = ["repair"]
```

- [ ] **Step 2: Create core/repair/utils.py**

Extract from `core/autofix.py` lines 28-160: `_force_plan_target_to_file`, `_resolve_semantic_target`, `_infer_provider_from_imports`, `_build_semantic_prelude`.

```python
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def force_plan_target_to_file(plan: dict[str, Any], file_path: str | None) -> dict[str, Any]:
    if not isinstance(plan, dict) or not file_path:
        return plan

    try:
        fp_path = Path(file_path).resolve()
        fp = str(fp_path)
    except Exception:
        fp_path = Path(str(file_path))
        fp = str(file_path)

    if not fp:
        return plan

    parent_fp = str(fp_path.parent)

    def _looks_like_directory_target(x: Any) -> bool:
        s = str(x) if x is not None else ""
        if s in {"", ".", parent_fp}:
            return True
        try:
            xp = Path(s)
            if xp.exists() and xp.is_dir():
                return True
        except Exception:
            pass
        return False

    target_files = plan.get("target_files")
    if not isinstance(target_files, list) or not target_files or any(_looks_like_directory_target(x) for x in target_files):
        plan["target_files"] = [fp]

    affected_scope = plan.get("affected_scope")
    if isinstance(affected_scope, list):
        if not affected_scope or any(_looks_like_directory_target(x) for x in affected_scope):
            plan["affected_scope"] = [fp]

    edits = plan.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                cur = edit.get("file")
                if _looks_like_directory_target(cur):
                    edit["file"] = fp

    evidence = plan.get("evidence")
    if isinstance(evidence, dict):
        loc = evidence.get("localization_target")
        if _looks_like_directory_target(loc):
            evidence["localization_target"] = fp

    for key in ("target_file", "file_path_hint"):
        cur = plan.get(key)
        if _looks_like_directory_target(cur):
            plan[key] = fp

    return plan


def resolve_semantic_target(file_path: str | None, semantic: dict[str, Any] | None) -> str | None:
    loc = (semantic or {}).get("localization") or {}
    top = loc.get("top") or {}
    top_file = top.get("file_path")
    if top_file and str(top_file).endswith(".py") and "/usr/lib/" not in str(top_file):
        return str(Path(top_file).resolve())
    return file_path


def infer_provider_from_imports(file_path: str | None) -> str | None:
    if not file_path or not str(file_path).endswith(".py"):
        return None
    p = Path(file_path)
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return None
    root = p.parent
    candidates: list[Path] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                mod_path = root / (node.module.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                mod_path = root / (alias.name.replace(".", "/") + ".py")
                if mod_path.exists():
                    candidates.append(mod_path)
    if not candidates:
        return None
    for c in candidates:
        if c.name != p.name:
            return str(c.resolve())
    return str(candidates[0].resolve())


def build_semantic_prelude(error_text: str, file_path: str | None) -> dict[str, Any]:
    from core.repro.harness import run_python_file, run_shell_text
    from core.semantic.fault_localizer import localize_fault, summarize_suspicions

    forced = "FORCED_SEMANTIC_ANALYSIS" in (error_text or "")

    if file_path and str(file_path).endswith(".py") and not forced:
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
        }

    if forced and file_path and str(file_path).endswith(".py"):
        caller = str(Path(file_path).resolve())
        provider = infer_provider_from_imports(file_path)
        items = [{
            "file_path": caller,
            "line_no": None,
            "symbol": None,
            "reason": "forced semantic caller seed",
            "score": 0.91,
        }]
        if provider:
            items.append({
                "file_path": provider,
                "line_no": None,
                "symbol": None,
                "reason": "forced semantic provider seed",
                "score": 0.97,
            })
        return {
            "repro": {
                "ok": True,
                "command": [],
                "cwd": str(Path(file_path).resolve().parent),
                "returncode": 0,
                "stdout": "",
                "stderr": error_text,
                "exception_type": "ForcedSemanticAnalysis",
                "reproduced": False,
            },
            "localization": {
                "count": len(items),
                "top": items[1] if len(items) > 1 else items[0],
                "items": items,
            },
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict(),
        "localization": summarize_suspicions(suspicions),
    }
```

- [ ] **Step 3: Create core/repair/events.py**

```python
from __future__ import annotations

from typing import Any

from core.ui.thoughts import ThoughtEvent
from core.memory import event_store


def emit_thought(
    thought_bus: Any,
    phase: str,
    message: str,
    *,
    kind: str = "info",
    confidence: float | None = None,
    file_path: str | None = None,
    line_no: int | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if thought_bus is None:
        return
    try:
        thought_bus.emit(
            ThoughtEvent(
                phase=phase,
                message=message,
                kind=kind,
                confidence=confidence,
                file_path=file_path,
                line_no=line_no,
                meta=meta or {},
            )
        )
    except Exception:
        pass


class EventStoreAdapter:
    def append_event(self, payload: dict[str, Any]) -> None:
        if hasattr(event_store, "append_event"):
            event_store.append_event(payload)
            return
        if hasattr(event_store, "store_event"):
            event_store.store_event(payload)
            return
        if hasattr(event_store, "write_event"):
            event_store.write_event(payload)
            return
```

- [ ] **Step 4: Create core/repair/hot_cache.py**

Extract hot cache boost logic from `core/autofix.py` lines ~750-850.

```python
from __future__ import annotations

from typing import Any


def boost_confidence(base_score: float, error_text: str) -> dict[str, Any]:
    """Boost confidence based on error pattern matching in hot cache."""
    from core.memory.engine import MemoryEngine

    engine = MemoryEngine()
    cached = engine.find_similar(error_text, limit=3)

    if not cached:
        return {"confidence": base_score, "recommendation": "human_review", "factors": {}}

    avg_prior = sum(r.confidence for r in cached) / len(cached) if cached else 0.0
    boosted = min(base_score + avg_prior * 0.3, 0.99)

    recommendation = "auto_apply" if boosted >= 0.85 else "apply_with_review" if boosted >= 0.6 else "human_review"

    return {
        "confidence": boosted,
        "recommendation": recommendation,
        "factors": {"hot_cache_avg_prior": avg_prior, "cached_records": len(cached)},
    }


def attach_hot_cache_boost(payload: dict[str, Any], *, error_text: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    base_score = float(((payload.get("confidence") or {}).get("score")) or 0.0)
    hot = boost_confidence(base_score, error_text)

    payload.setdefault("memory", {})
    payload["memory"]["hot_cache"] = hot

    verify_ok = bool((payload.get("verify") or {}).get("ok"))
    conf = payload.get("confidence") or {}
    if verify_ok and isinstance(conf, dict):
        old_score = float(conf.get("score", 0.0) or 0.0)
        new_score = max(old_score, float(hot.get("confidence", old_score) or old_score))
        conf["score"] = new_score
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = new_score - old_score
        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

    return payload


def apply_hot_cache_to_payload(payload: dict[str, Any], *, error_text: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    payload.setdefault("memory", {})
    conf = payload.get("confidence") or {}
    if not isinstance(conf, dict):
        conf = {}
    payload["confidence"] = conf

    result = payload.get("result") or {}
    best_plan = payload.get("best_plan") or {}
    base_score = float(
        conf.get("score", 0.0)
        or (result.get("confidence") if isinstance(result, dict) else 0.0)
        or (best_plan.get("confidence") if isinstance(best_plan, dict) else 0.0)
        or 0.0
    )

    hot = boost_confidence(base_score, error_text)
    payload["memory"]["hot_cache"] = hot

    verify_ok = bool((payload.get("verify") or {}).get("ok"))
    if verify_ok:
        boosted = max(base_score, float(hot.get("confidence", base_score) or base_score))
        conf["score"] = boosted
        conf.setdefault("factors", {})
        conf["factors"]["hot_cache"] = boosted - base_score
        if hot.get("recommendation") == "auto_apply":
            conf["recommendation"] = "auto_apply"

    return payload
```

- [ ] **Step 5: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add core/repair/__init__.py core/repair/utils.py core/repair/events.py core/repair/hot_cache.py
git commit -m "feat(v2): create core/repair package skeleton with utils, events, hot_cache"
```

---

## Task 2: Create core/repair/candidates.py and core/repair/planner.py

**Covers:** S1 (autofix.py split)

**Files:**
- Create: `core/repair/candidates.py`
- Create: `core/repair/planner.py`
- Create: `core/repair/verify.py`

- [ ] **Step 1: Create core/repair/candidates.py**

Extract candidate generation from `core/autofix.py` `_build_candidates` function.

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.experts.file_runtime import FileRuntimeExpert
from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.ui.thoughts import ThoughtEvent


def build_candidates(
    error_text: str,
    file_path: str | None,
    semantic: dict[str, Any] | None = None,
    thought_bus: Any = None,
) -> list[dict[str, Any]]:
    from .utils import resolve_semantic_target

    ctx = type("Ctx", (), {})()
    semantic_target = resolve_semantic_target(file_path, semantic)
    ctx.error_text = error_text
    ctx.file_path = semantic_target or file_path
    source_target = semantic_target or file_path

    if source_target:
        try:
            ctx.source_code = Path(source_target).read_text(encoding="utf-8")
        except Exception:
            ctx.source_code = ""
    else:
        ctx.source_code = ""

    candidates: list[dict[str, Any]] = []
    for expert in (
        FileRuntimeExpert(),
        PythonSyntaxExpert(),
        DependencyExpert(),
        ShellRuntimeExpert(),
        MemoryRetrievalExpert(),
        LLMFallbackExpert(),
    ):
        try:
            proposed = expert.propose(ctx) or []
            for item in proposed:
                if isinstance(item, dict):
                    candidates.append(item)
        except Exception:
            continue

    if thought_bus is not None:
        try:
            thought_bus.emit(
                ThoughtEvent(
                    phase="Candidate Generation",
                    message=f"{len(candidates)} candidates produced",
                    kind="info",
                )
            )
            expert_names = sorted({str((c or {}).get("expert") or "unknown") for c in candidates if isinstance(c, dict)})
            thought_bus.emit(
                ThoughtEvent(
                    phase="Expert Routing",
                    message="experts=" + ", ".join(expert_names),
                    kind="info",
                )
            )
        except Exception:
            pass

    return candidates
```

- [ ] **Step 2: Create core/repair/planner.py**

```python
from __future__ import annotations

from typing import Any

from core.planner.repair_planner import build_repair_plans
from core.planner.multi_file_planner import expand_multifile_plan_family
from core.ranker.ranker import rank_plans
from core.contracts.checker import synthesize_and_check_contract, check_contract_propagation
from .utils import force_plan_target_to_file
from .events import emit_thought


def build_and_rank_plans(
    error_text: str,
    semantic: dict[str, Any] | None,
    causes: list[dict[str, Any]],
    project_graph: dict[str, Any],
    candidates: list[dict[str, Any]],
    file_path: str | None,
    thought_bus: Any = None,
) -> list[dict[str, Any]]:
    base_plans = build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=project_graph,
        candidates=candidates,
        file_path=file_path,
    )

    multifile_plans = expand_multifile_plan_family(
        base_plans=base_plans,
        file_path=file_path,
        semantic=semantic,
    )

    emit_thought(thought_bus, "Planning", f"base_plans={len(base_plans)} multifile_plans={len(multifile_plans)}")
    emit_thought(thought_bus, "Plan Expansion", f"total_plans={len(base_plans) + len(multifile_plans)}")

    all_plans = list(base_plans) + list(multifile_plans)
    enriched = []

    for plan in all_plans:
        plan = force_plan_target_to_file(plan, file_path)
        branch = None
        if file_path:
            from core.planner.branch_executor import execute_repair_plan
            branch = execute_repair_plan(plan, file_path)

        contract = synthesize_and_check_contract(
            before_error_text=error_text,
            branch_result=branch or {},
            expected_behavior=plan.get("expected_behavior", {}),
        )

        p2 = dict(plan)
        p2["branch_result"] = branch
        p2["contract_result"] = contract
        p2["contract_propagation"] = check_contract_propagation(p2)
        enriched.append(p2)

    ranked = rank_plans(enriched)

    if ranked:
        best = ranked[0]
        evidence = best.get("evidence") or {}
        strategy = evidence.get("strategy") or "unknown"
        target = ((best.get("edits") or [{}])[0].get("file")) or best.get("target_file")
        emit_thought(
            thought_bus,
            "Winner Selection",
            f"strategy={strategy} target={target}",
            kind="info",
            confidence=best.get("confidence"),
            file_path=target,
        )

    return ranked
```

- [ ] **Step 3: Create core/repair/verify.py**

```python
from __future__ import annotations

from typing import Any

from core.verify.sandbox import run_in_sandbox
from core.contracts.checker import synthesize_and_check_contract


def verify_repair(
    plan: dict[str, Any],
    file_path: str | None,
    error_text: str,
) -> dict[str, Any]:
    if not file_path:
        return {"ok": False, "reason": "no file to verify"}

    edits = plan.get("edits") or []
    if not edits:
        return {"ok": False, "reason": "no edits in plan"}

    sandbox_result = run_in_sandbox(file_path)

    contract = synthesize_and_check_contract(
        before_error_text=error_text,
        branch_result=sandbox_result.to_dict() if hasattr(sandbox_result, "to_dict") else sandbox_result,
        expected_behavior=plan.get("expected_behavior", {}),
    )

    return {
        "ok": sandbox_result.ok if hasattr(sandbox_result, "ok") else False,
        "sandbox": sandbox_result.to_dict() if hasattr(sandbox_result, "to_dict") else sandbox_result,
        "contract": contract,
    }
```

- [ ] **Step 4: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add core/repair/candidates.py core/repair/planner.py core/repair/verify.py
git commit -m "feat(v2): add candidates, planner, verify modules to core/repair"
```

---

## Task 3: Create core/repair/engine.py — main orchestration

**Covers:** S1 (autofix.py split)

**Files:**
- Create: `core/repair/engine.py`

- [ ] **Step 1: Create core/repair/engine.py**

```python
from __future__ import annotations

from typing import Any
from pathlib import Path
from time import perf_counter
import uuid

from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.memory import event_store
from core.ui.thoughts import ThoughtEvent

from .utils import build_semantic_prelude
from .candidates import build_candidates
from .planner import build_and_rank_plans
from .verify import verify_repair
from .hot_cache import attach_hot_cache_boost, apply_hot_cache_to_payload
from .events import emit_thought, EventStoreAdapter


def repair(
    error_text: str,
    file_path: str | None = None,
    *,
    fast: bool = False,
    thought_bus: Any = None,
) -> dict[str, Any]:
    start = perf_counter()
    run_id = str(uuid.uuid4())

    semantic = build_semantic_prelude(error_text, file_path)

    emit_thought(thought_bus, "Reproduction", "repro complete", kind="info")
    if semantic.get("localization"):
        top = semantic["localization"].get("top")
        if top:
            emit_thought(
                thought_bus,
                "Fault Localization",
                f"top suspect: {top.get('file_path')}:{top.get('line_no')}",
                kind="info",
                confidence=top.get("score"),
                file_path=top.get("file_path"),
                line_no=top.get("line_no"),
            )

    graph = build_project_graph(file_path).to_dict() if file_path else {"project_root": str("."), "files": [], "adjacency": {}}

    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
    )]

    candidates = build_candidates(
        error_text=error_text,
        file_path=file_path,
        semantic=semantic,
        thought_bus=thought_bus,
    )

    ranked = build_and_rank_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
        candidates=candidates,
        file_path=file_path,
        thought_bus=thought_bus,
    )

    if not ranked:
        result = {
            "ok": False,
            "run_id": run_id,
            "error_text": error_text,
            "file_path": file_path,
            "elapsed_ms": int((perf_counter() - start) * 1000),
            "ranked_plans": 0,
        }
        return result

    best = ranked[0]
    verification = verify_repair(best, file_path, error_text)

    payload = {
        "ok": verification.get("ok", False),
        "run_id": run_id,
        "error_text": error_text,
        "file_path": file_path,
        "elapsed_ms": int((perf_counter() - start) * 1000),
        "ranked_plans": len(ranked),
        "best_plan": best,
        "verify": verification,
        "semantic": semantic,
        "candidates_count": len(candidates),
        "causes_count": len(causes),
    }

    payload = apply_hot_cache_to_payload(payload, error_text=error_text)

    adapter = EventStoreAdapter()
    adapter.append_event(payload)

    emit_thought(thought_bus, "Complete", f"repair {'succeeded' if payload['ok'] else 'failed'}", kind="success" if payload["ok"] else "warning")

    return payload
```

- [ ] **Step 2: Update core/repair/__init__.py**

```python
from __future__ import annotations

from .engine import repair
from .candidates import build_candidates
from .planner import build_and_rank_plans
from .verify import verify_repair
from .hot_cache import boost_confidence, attach_hot_cache_boost, apply_hot_cache_to_payload
from .utils import force_plan_target_to_file, resolve_semantic_target, infer_provider_from_imports, build_semantic_prelude
from .events import emit_thought, EventStoreAdapter

__all__ = [
    "repair",
    "build_candidates",
    "build_and_rank_plans",
    "verify_repair",
    "boost_confidence",
    "attach_hot_cache_boost",
    "apply_hot_cache_to_payload",
    "force_plan_target_to_file",
    "resolve_semantic_target",
    "infer_provider_from_imports",
    "build_semantic_prelude",
    "emit_thought",
    "EventStoreAdapter",
]
```

- [ ] **Step 3: Make core/autofix.py a backward-compat shim**

Replace the body of `core/autofix.py` with imports from `core.repair`:

```python
from __future__ import annotations

"""Backward-compatible shim — all logic moved to core.repair."""
from core.repair import (
    repair,
    build_candidates,
    build_and_rank_plans,
    verify_repair,
    boost_confidence,
    attach_hot_cache_boost,
    apply_hot_cache_to_payload,
    force_plan_target_to_file,
    resolve_semantic_target,
    infer_provider_from_imports,
    build_semantic_prelude,
    emit_thought,
    EventStoreAdapter,
)

# Re-export the main entry point
__all__ = [
    "repair",
    "build_candidates",
    "build_and_rank_plans",
    "verify_repair",
    "boost_confidence",
    "attach_hot_cache_boost",
    "apply_hot_cache_to_payload",
    "force_plan_target_to_file",
    "resolve_semantic_target",
    "infer_provider_from_imports",
    "build_semantic_prelude",
    "emit_thought",
    "EventStoreAdapter",
]
```

- [ ] **Step 4: Run existing tests to verify backward compat**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -x --timeout=30 2>&1 | head -50`
Expected: Tests pass (or at least don't fail on import)

- [ ] **Step 5: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add core/repair/engine.py core/repair/__init__.py core/autofix.py
git commit -m "feat(v2): add engine.py, update autofix.py to backward-compat shim"
```

---

## Task 4: Plugin API v2

**Covers:** S2 (Plugin API)

**Files:**
- Create: `core/plugins/__init__.py`
- Create: `core/plugins/base.py`
- Create: `core/plugins/registry.py`
- Create: `core/plugins/builtin/__init__.py`
- Create: `core/plugins/builtin/python_hotfix.py`
- Modify: `core/mimo/tools/registry.py`

- [ ] **Step 1: Create core/plugins/base.py**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.experts.base import RepairExpert
from core.mimo.tools import Tool


class Plugin(ABC):
    """Base class for TermOrganism plugins."""
    
    name: str = "base"
    version: str = "0.1.0"
    description: str = ""

    def register_experts(self) -> list[RepairExpert]:
        return []

    def register_tools(self) -> list[Tool]:
        return []

    def on_repair_start(self, context: dict[str, Any]) -> None:
        pass

    def on_repair_complete(self, result: dict[str, Any]) -> None:
        pass
```

- [ ] **Step 2: Create core/plugins/registry.py**

```python
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml

from .base import Plugin
from core.experts.base import RepairExpert
from core.mimo.tools import Tool


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._experts: list[RepairExpert] = []
        self._tools: list[Tool] = []

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.name] = plugin
        self._experts.extend(plugin.register_experts())
        self._tools.extend(plugin.register_tools())

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def get_experts(self) -> list[RepairExpert]:
        return list(self._experts)

    def get_tools(self) -> list[Tool]:
        return list(self._tools)

    def notify_repair_start(self, context: dict[str, Any]) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_repair_start(context)
            except Exception:
                pass

    def notify_repair_complete(self, result: dict[str, Any]) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_repair_complete(result)
            except Exception:
                pass


def load_plugins_from_config(config_path: str | None = None) -> PluginRegistry:
    registry = PluginRegistry()

    if config_path is None:
        from core.mimo.config import get_config
        config = get_config()
        config_path = getattr(config, "plugins_path", None)

    if config_path and Path(config_path).exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            for plugin_spec in cfg.get("plugins", []):
                if isinstance(plugin_spec, str):
                    module_path = plugin_spec
                elif isinstance(plugin_spec, dict):
                    module_path = plugin_spec.get("module", "")
                else:
                    continue
                try:
                    mod = importlib.import_module(module_path)
                    plugin_cls = getattr(mod, "Plugin", None)
                    if plugin_cls and issubclass(plugin_cls, Plugin):
                        registry.register(plugin_cls())
                except Exception:
                    continue
        except Exception:
            pass

    # Always load built-in plugins
    try:
        from core.plugins.builtin.python_hotfix import PythonHotfixPlugin
        registry.register(PythonHotfixPlugin())
    except Exception:
        pass

    return registry
```

- [ ] **Step 3: Create core/plugins/builtin/python_hotfix.py**

```python
from __future__ import annotations

from typing import Any

from core.plugins.base import Plugin
from core.experts.base import RepairExpert
from core.mimo.tools import Tool


class PythonHotfixExpert(RepairExpert):
    name = "python_hotfix"
    supported_languages = {"python"}

    def score(self, ctx: Any) -> tuple[float, list[str]]:
        return 0.5, ["python-hotfix plugin"]

    def propose(self, ctx: Any) -> list[dict[str, Any]]:
        return []


class PythonHotfixPlugin(Plugin):
    name = "python-hotfix"
    version = "1.0.0"
    description = "Built-in Python hotfix plugin"

    def register_experts(self) -> list[RepairExpert]:
        return [PythonHotfixExpert()]

    def register_tools(self) -> list[Tool]:
        return []
```

- [ ] **Step 4: Create core/plugins/__init__.py**

```python
from __future__ import annotations

from .base import Plugin
from .registry import PluginRegistry, load_plugins_from_config

__all__ = ["Plugin", "PluginRegistry", "load_plugins_from_config"]
```

- [ ] **Step 5: Create core/plugins/builtin/__init__.py**

```python
```

- [ ] **Step 6: Update core/mimo/tools/registry.py to support plugin tools**

Add a method to `ToolRegistry`:

```python
def register_all(self, tools: list[Tool]) -> None:
    for tool in tools:
        self.register(tool)
```

- [ ] **Step 7: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add core/plugins/
git commit -m "feat(v2): add plugin API with base class, registry, and builtin python-hotfix"
```

---

## Task 5: Test coverage — repair modules

**Covers:** S3 (Test coverage)

**Files:**
- Create: `tests/test_repair_engine.py`
- Create: `tests/test_repair_candidates.py`
- Create: `tests/test_repair_planner.py`
- Create: `tests/test_repair_verify.py`
- Create: `tests/test_repair_hot_cache.py`
- Create: `tests/test_repair_utils.py`

- [ ] **Step 1: Create tests/test_repair_utils.py**

```python
from __future__ import annotations

from core.repair.utils import force_plan_target_to_file, resolve_semantic_target


def test_force_plan_target_to_file_sets_target():
    plan = {"target_files": [], "edits": [{"file": None}]}
    result = force_plan_target_to_file(plan, "/tmp/test.py")
    assert result["target_files"] == ["/tmp/test.py"]
    assert result["edits"][0]["file"] == "/tmp/test.py"


def test_force_plan_target_to_file_no_change_with_valid_target():
    plan = {"target_files": ["/tmp/other.py"]}
    result = force_plan_target_to_file(plan, "/tmp/test.py")
    assert result["target_files"] == ["/tmp/other.py"]


def test_resolve_semantic_target_returns_file_path():
    semantic = {"localization": {"top": {"file_path": "/tmp/test.py"}}}
    result = resolve_semantic_target("/tmp/other.py", semantic)
    assert result == "/tmp/test.py"


def test_resolve_semantic_target_returns_original_when_no_semantic():
    result = resolve_semantic_target("/tmp/test.py", None)
    assert result == "/tmp/test.py"


def test_resolve_semantic_target_skips_stdlib():
    semantic = {"localization": {"top": {"file_path": "/usr/lib/python3.10/os.py"}}}
    result = resolve_semantic_target("/tmp/test.py", semantic)
    assert result == "/tmp/test.py"
```

- [ ] **Step 2: Create tests/test_repair_hot_cache.py**

```python
from __future__ import annotations

from core.repair.hot_cache import boost_confidence, attach_hot_cache_boost, apply_hot_cache_to_payload


def test_boost_confidence_returns_base_when_no_cache():
    result = boost_confidence(0.5, "some error")
    assert "confidence" in result
    assert result["recommendation"] in ("auto_apply", "apply_with_review", "human_review")


def test_attach_hot_cache_boost_adds_memory():
    payload = {"confidence": {"score": 0.5}}
    result = attach_hot_cache_boost(payload, error_text="test error")
    assert "memory" in result
    assert "hot_cache" in result["memory"]


def test_apply_hot_cache_to_payload_structure():
    payload = {"confidence": {"score": 0.5}}
    result = apply_hot_cache_to_payload(payload, error_text="test error")
    assert "memory" in result
    assert "hot_cache" in result["memory"]
```

- [ ] **Step 3: Create tests/test_repair_candidates.py**

```python
from __future__ import annotations

from unittest.mock import patch, MagicMock
from core.repair.candidates import build_candidates


def test_build_candidates_returns_list():
    result = build_candidates("error", None, None)
    assert isinstance(result, list)


def test_build_candidates_with_file():
    result = build_candidates("error", "/tmp/nonexistent.py", None)
    assert isinstance(result, list)
```

- [ ] **Step 4: Create tests/test_repair_planner.py**

```python
from __future__ import annotations

from unittest.mock import patch
from core.repair.planner import build_and_rank_plans


@patch("core.repair.planner.build_repair_plans", return_value=[])
@patch("core.repair.planner.expand_multifile_plan_family", return_value=[])
@patch("core.repair.planner.rank_plans", return_value=[])
def test_build_and_rank_plans_empty(mock_rank, mock_expand, mock_build):
    result = build_and_rank_plans("error", None, [], {}, [], None)
    assert result == []
    mock_build.assert_called_once()
```

- [ ] **Step 5: Create tests/test_repair_verify.py**

```python
from __future__ import annotations

from core.repair.verify import verify_repair


def test_verify_repair_no_file():
    result = verify_repair({}, None, "error")
    assert result["ok"] is False
    assert "no file" in result["reason"]


def test_verify_repair_no_edits():
    result = verify_repair({"edits": []}, "/tmp/test.py", "error")
    assert result["ok"] is False
```

- [ ] **Step 6: Create tests/test_repair_engine.py**

```python
from __future__ import annotations

from unittest.mock import patch
from core.repair.engine import repair


@patch("core.repair.engine.build_semantic_prelude", return_value={"repro": {}, "localization": {}})
@patch("core.repair.engine.build_candidates", return_value=[])
@patch("core.repair.engine.build_and_rank_plans", return_value=[])
def test repair_returns_ok_false_on_no_plans(mock_plans, mock_candidates, mock_prelude):
    result = repair("error", None)
    assert result["ok"] is False
    assert result["ranked_plans"] == 0
```

- [ ] **Step 7: Run all new tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_repair_*.py -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add tests/test_repair_*.py
git commit -m "test(v2): add unit tests for core/repair modules"
```

---

## Task 6: Test coverage — expert tests

**Covers:** S3 (Test coverage)

**Files:**
- Create: `tests/test_expert_file_runtime.py`
- Create: `tests/test_expert_python_syntax.py`
- Create: `tests/test_expert_dependency.py`
- Create: `tests/test_expert_shell_runtime.py`
- Create: `tests/test_expert_memory_retrieval.py`
- Create: `tests/test_expert_llm_fallback.py`

- [ ] **Step 1: Create tests/test_expert_file_runtime.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.file_runtime import FileRuntimeExpert


def test_file_runtime_expert_has_name():
    expert = FileRuntimeExpert()
    assert expert.name


def test_file_runtime_expert_propose_returns_list():
    expert = FileRuntimeExpert()
    ctx = FailureContext(error_text="FileNotFoundError")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 2: Create tests/test_expert_python_syntax.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.python_syntax import PythonSyntaxExpert


def test_python_syntax_expert_has_name():
    expert = PythonSyntaxExpert()
    assert expert.name


def test_python_syntax_expert_propose_returns_list():
    expert = PythonSyntaxExpert()
    ctx = FailureContext(error_text="SyntaxError: invalid syntax")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 3: Create tests/test_expert_dependency.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.dependency import DependencyExpert


def test_dependency_expert_has_name():
    expert = DependencyExpert()
    assert expert.name


def test_dependency_expert_propose_returns_list():
    expert = DependencyExpert()
    ctx = FailureContext(error_text="ModuleNotFoundError: No module named 'foo'")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 4: Create tests/test_expert_shell_runtime.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.shell_runtime import ShellRuntimeExpert


def test_shell_runtime_expert_has_name():
    expert = ShellRuntimeExpert()
    assert expert.name


def test_shell_runtime_expert_propose_returns_list():
    expert = ShellRuntimeExpert()
    ctx = FailureContext(error_text="bash: command not found")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 5: Create tests/test_expert_memory_retrieval.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.memory_retrieval import MemoryRetrievalExpert


def test_memory_retrieval_expert_has_name():
    expert = MemoryRetrievalExpert()
    assert expert.name


def test_memory_retrieval_expert_propose_returns_list():
    expert = MemoryRetrievalExpert()
    ctx = FailureContext(error_text="some error")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 6: Create tests/test_expert_llm_fallback.py**

```python
from __future__ import annotations

from core.models.schemas import FailureContext
from core.experts.llm_fallback import LLMFallbackExpert


def test_llm_fallback_expert_has_name():
    expert = LLMFallbackExpert()
    assert expert.name


def test_llm_fallback_expert_propose_returns_list():
    expert = LLMFallbackExpert()
    ctx = FailureContext(error_text="some error")
    result = expert.propose(ctx)
    assert isinstance(result, list)
```

- [ ] **Step 7: Run all expert tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_expert_*.py -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add tests/test_expert_*.py
git commit -m "test(v2): add unit tests for all repair experts"
```

---

## Task 7: Test coverage — tool tests

**Covers:** S3 (Test coverage)

**Files:**
- Create: `tests/test_tool_bash.py`
- Create: `tests/test_tool_file_read.py`
- Create: `tests/test_tool_file_write.py`
- Create: `tests/test_tool_edit.py`
- Create: `tests/test_tool_glob.py`
- Create: `tests/test_tool_grep.py`
- Create: `tests/test_tool_git.py`
- Create: `tests/test_tool_task.py`
- Create: `tests/test_tool_question.py`
- Create: `tests/test_tool_memory.py`

- [ ] **Step 1: Create tests/test_tool_bash.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.bash import BashTool


@pytest.mark.asyncio
async def test_bash_tool_executes_command():
    tool = BashTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_bash_tool_handles_error():
    tool = BashTool()
    result = await tool.execute(command="exit 1")
    assert "error" in result.lower() or "returncode" in result.lower() or "1" in result
```

- [ ] **Step 2: Create tests/test_tool_file_read.py**

```python
from __future__ import annotations

import pytest
from pathlib import Path
from core.mimo.tools.file_read import FileReadTool


@pytest.mark.asyncio
async def test_file_read_tool_reads_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    tool = FileReadTool()
    result = await tool.execute(file_path=str(test_file))
    assert "hello world" in result


@pytest.mark.asyncio
async def test_file_read_tool_missing_file():
    tool = FileReadTool()
    result = await tool.execute(file_path="/tmp/nonexistent_file_12345.txt")
    assert "error" in result.lower() or "not found" in result.lower()
```

- [ ] **Step 3: Create tests/test_tool_file_write.py**

```python
from __future__ import annotations

import pytest
from pathlib import Path
from core.mimo.tools.file_write import FileWriteTool


@pytest.mark.asyncio
async def test_file_write_tool_creates_file(tmp_path):
    test_file = tmp_path / "test.txt"
    tool = FileWriteTool()
    result = await tool.execute(file_path=str(test_file), content="hello")
    assert "success" in result.lower() or "written" in result.lower()
    assert test_file.read_text() == "hello"
```

- [ ] **Step 4: Create tests/test_tool_edit.py**

```python
from __future__ import annotations

import pytest
from pathlib import Path
from core.mimo.tools.edit import EditTool


@pytest.mark.asyncio
async def test_edit_tool_replaces_string(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    tool = EditTool()
    result = await tool.execute(file_path=str(test_file), old_string="hello", new_string="goodbye")
    assert "success" in result.lower() or "edited" in result.lower() or "replaced" in result.lower()
    assert test_file.read_text() == "goodbye world"
```

- [ ] **Step 5: Create tests/test_tool_glob.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.glob import GlobTool


@pytest.mark.asyncio
async def test_glob_tool_finds_files(tmp_path):
    (tmp_path / "test.py").write_text("")
    tool = GlobTool()
    result = await tool.execute(pattern="*.py", path=str(tmp_path))
    assert "test.py" in result
```

- [ ] **Step 6: Create tests/test_tool_grep.py**

```python
from __future__ import annotations

import pytest
from pathlib import Path
from core.mimo.tools.grep import GrepTool


@pytest.mark.asyncio
async def test_grep_tool_finds_pattern(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    pass")
    tool = GrepTool()
    result = await tool.execute(pattern="hello", path=str(tmp_path))
    assert "hello" in result
```

- [ ] **Step 7: Create tests/test_tool_git.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.git import GitTool


@pytest.mark.asyncio
async def test_git_tool_status():
    tool = GitTool()
    result = await tool.execute(command="status")
    assert isinstance(result, str)
```

- [ ] **Step 8: Create tests/test_tool_task.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.task import TaskTool


@pytest.mark.asyncio
async def test_task_tool_creates_task():
    tool = TaskTool()
    result = await tool.execute(operation="create", summary="Test task")
    assert isinstance(result, str)
```

- [ ] **Step 9: Create tests/test_tool_question.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.question import QuestionTool


def test_question_tool_has_name():
    tool = QuestionTool()
    assert tool.name()
```

- [ ] **Step 10: Create tests/test_tool_memory.py**

```python
from __future__ import annotations

import pytest
from core.mimo.tools.memory import MemoryTool


def test_memory_tool_has_name():
    tool = MemoryTool()
    assert tool.name()
```

- [ ] **Step 11: Run all tool tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_tool_*.py -v`
Expected: All pass

- [ ] **Step 12: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add tests/test_tool_*.py
git commit -m "test(v2): add unit tests for all MIMO tools"
```

---

## Task 8: Test coverage — plugin tests

**Covers:** S2 (Plugin API), S3 (Test coverage)

**Files:**
- Create: `tests/test_plugin_api.py`
- Create: `tests/test_plugin_registry.py`

- [ ] **Step 1: Create tests/test_plugin_api.py**

```python
from __future__ import annotations

from core.plugins.base import Plugin
from core.experts.base import RepairExpert


class DummyPlugin(Plugin):
    name = "dummy"
    version = "0.1.0"

    def register_experts(self):
        return []

    def register_tools(self):
        return []


def test_plugin_has_name():
    plugin = DummyPlugin()
    assert plugin.name == "dummy"


def test_plugin_register_experts_returns_list():
    plugin = DummyPlugin()
    assert plugin.register_experts() == []


def test_plugin_register_tools_returns_list():
    plugin = DummyPlugin()
    assert plugin.register_tools() == []


def test_plugin_on_repair_start_does_not_raise():
    plugin = DummyPlugin()
    plugin.on_repair_start({"error": "test"})


def test_plugin_on_repair_complete_does_not_raise():
    plugin = DummyPlugin()
    plugin.on_repair_complete({"ok": True})
```

- [ ] **Step 2: Create tests/test_plugin_registry.py**

```python
from __future__ import annotations

from core.plugins.base import Plugin
from core.plugins.registry import PluginRegistry


class DummyPlugin(Plugin):
    name = "dummy"
    version = "0.1.0"


def test_plugin_registry_register():
    registry = PluginRegistry()
    plugin = DummyPlugin()
    registry.register(plugin)
    assert registry.get("dummy") is plugin


def test_plugin_registry_list_plugins():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    assert len(registry.list_plugins()) == 1


def test_plugin_registry_notify_does_not_raise():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    registry.notify_repair_start({"error": "test"})
    registry.notify_repair_complete({"ok": True})
```

- [ ] **Step 3: Run plugin tests**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/test_plugin_*.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add tests/test_plugin_*.py
git commit -m "test(v2): add unit tests for plugin API and registry"
```

---

## Task 9: CI/CD — GitHub Actions

**Covers:** S4 (CI/CD)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create .github/workflows/ci.yml**

```yaml
name: CI

on:
  push:
    branches: [main, milestone/*]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check core/ tests/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v --timeout=60

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install mypy
      - run: mypy core/ --ignore-missing-imports --no-strict-optional
```

- [ ] **Step 2: Commit**

```bash
cd /home/craftzzdog/TermOrganism
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci(v2): add GitHub Actions workflow for lint, test, typecheck"
```

---

## Task 10: pyproject.toml update

**Covers:** S4 (CI/CD), S5 (Cleanup)

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "termorganism"
version = "0.2.0"
description = "AI-powered code repair engine with semantic routing, behavioral verification, and plugin API"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = [
    "rich>=13.0",
    "aiohttp>=3.9",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.4.0",
    "mypy>=1.10",
]

[project.scripts]
termorganism = "core.cli.autofix_cli:main"
termorg = "core.mimo.repl:main"
termorganism-watch = "core.watch.watch_cli:main"

[tool.setuptools.packages.find]
include = ["core*"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
```

- [ ] **Step 2: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add pyproject.toml
git commit -m "chore(v2): bump version to 0.2.0, add dev deps, entry points, ruff/mypy config"
```

---

## Task 11: Cleanup — remove legacy scripts and archive

**Covers:** S5 (Cleanup)

**Files:**
- Delete: `restructure_termorganism.sh`
- Delete: `relocate_from_core.sh`

- [ ] **Step 1: Delete legacy scripts**

```bash
cd /home/craftzzdog/TermOrganism
rm restructure_termorganism.sh relocate_from_core.sh
```

- [ ] **Step 2: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add -u restructure_termorganism.sh relocate_from_core.sh
git commit -m "chore(v2): remove legacy migration scripts"
```

---

## Task 12: Documentation — changelog and README update

**Covers:** S4 (Docs)

**Files:**
- Create: `docs/v2-changelog.md`
- Modify: `README.md`

- [ ] **Step 1: Create docs/v2-changelog.md**

```markdown
# TermOrganism v2.0.0 Changelog

## Breaking Changes
- `core/autofix.py` is now a backward-compatibility shim. All logic lives in `core/repair/`.
- Plugin API is now the official way to extend experts and tools.

## New Features
- **Plugin API v2**: Plugins can register custom experts and tools via `core/plugins/base.py`
- **Modular repair engine**: `core/repair/` package with separate modules for candidates, planning, verification, hot cache, and events
- **CI/CD**: GitHub Actions for lint (ruff), test (pytest), typecheck (mypy)
- **Expanded test coverage**: ~70+ tests across repair, experts, tools, and plugins

## Improvements
- Version bumped to 0.2.0
- Added `termorg` and `termorganism-watch` entry points to pyproject.toml
- Added ruff and mypy configuration
- Removed legacy migration scripts (`restructure_termorganism.sh`, `relocate_from_core.sh`)

## Internal
- `core/repair/engine.py` — main orchestration loop
- `core/repair/candidates.py` — expert candidate generation
- `core/repair/planner.py` — plan building and ranking
- `core/repair/verify.py` — sandbox verification helpers
- `core/repair/hot_cache.py` — hot cache boost logic
- `core/repair/events.py` — thought event emission
- `core/repair/utils.py` — shared utilities
- `core/plugins/` — plugin base class and registry
```

- [ ] **Step 2: Update README.md**

Add a "What's New in v2" section after the Quick Start section:

```markdown
## What's New in v2

- **Modular Architecture**: `core/autofix.py` split into focused modules under `core/repair/`
- **Plugin API**: Extend TermOrganism with custom experts and tools
- **CI/CD**: Automated linting, testing, and type checking via GitHub Actions
- **Expanded Tests**: 70+ unit tests covering all major components
```

- [ ] **Step 3: Commit**

```bash
cd /home/craftzzdog/TermOrganism
git add docs/v2-changelog.md README.md
git commit -m "docs(v2): add changelog and update README with v2 features"
```

---

## Task 13: Final verification — run full test suite

**Covers:** S3 (Test coverage)

- [ ] **Step 1: Run full test suite**

Run: `cd /home/craftzzdog/TermOrganism && python -m pytest tests/ -v --timeout=60`
Expected: All tests pass

- [ ] **Step 2: Run lint check**

Run: `cd /home/craftzzdog/TermOrganism && pip install ruff && ruff check core/ tests/`
Expected: No errors (or only warnings)

- [ ] **Step 3: Verify backward compatibility**

Run: `cd /home/craftzzdog/TermOrganism && python -c "from core.autofix import repair; print('OK')"`
Expected: `OK`

---

## Execution Handoff

This plan has 13 tasks with clear dependencies. Recommend **subagent execution** for parallel work on independent tasks (Tasks 5-8 can run in parallel).

To execute, invoke compose:subagent or compose:execute with this plan.
