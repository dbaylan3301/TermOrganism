from __future__ import annotations
from __future__ import annotations
#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/project/graph.py": r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import ast


@dataclass
class FileNode:
    path: str
    imports: list[str]
    functions: list[str]
    classes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectGraph:
    project_root: str
    files: list[FileNode]
    adjacency: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "files": [f.to_dict() for f in self.files],
            "adjacency": self.adjacency,
        }


def _guess_project_root(file_path: str | Path | None) -> Path:
    if not file_path:
        return Path.cwd()
    p = Path(file_path).resolve()
    cur = p.parent if p.is_file() else p
    markers = {".git", "pyproject.toml", "setup.py", "requirements.txt"}
    for base in [cur, *cur.parents]:
        if any((base / m).exists() for m in markers):
            return base
    return cur


def _parse_python_file(path: Path) -> FileNode:
    text = path.read_text(encoding="utf-8", errors="replace")
    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []

    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
    except Exception:
        pass

    return FileNode(
        path=str(path),
        imports=sorted(set(imports)),
        functions=sorted(set(functions)),
        classes=sorted(set(classes)),
    )


def build_project_graph(file_path: str | Path | None) -> ProjectGraph:
    root = _guess_project_root(file_path)
    py_files = sorted(root.rglob("*.py"))

    files: list[FileNode] = []
    file_names = {p.stem: str(p) for p in py_files}
    adjacency: dict[str, list[str]] = {}

    for py in py_files:
        node = _parse_python_file(py)
        files.append(node)

        neighbors: list[str] = []
        for imp in node.imports:
            base = imp.split(".")[0]
            if base in file_names:
                neighbors.append(file_names[base])
        adjacency[str(py)] = sorted(set(neighbors))

    return ProjectGraph(
        project_root=str(root),
        files=files,
        adjacency=adjacency,
    )
''',

    "core/causal/analyzer.py": r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CausalNode:
    node_id: str
    kind: str
    file_path: str
    reason: str
    score: float
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_failure_causes(*, error_text: str, semantic: dict[str, Any] | None = None, project_graph: dict[str, Any] | None = None) -> list[CausalNode]:
    text = (error_text or "").lower()
    localization_items = ((semantic or {}).get("localization") or {}).get("items") or []

    top_file = ""
    if localization_items:
        top_file = localization_items[0].get("file_path", "") or ""

    causes: list[CausalNode] = []

    if "filenotfounderror" in text or "no such file or directory" in text:
        causes.append(CausalNode(
            node_id="cause_missing_runtime_file",
            kind="missing_runtime_file",
            file_path=top_file,
            reason="runtime path or file invariant is broken",
            score=0.92,
            evidence={"error_family": "FileNotFoundError"},
        ))
        causes.append(CausalNode(
            node_id="cause_unsafe_io_boundary",
            kind="unsafe_io_boundary",
            file_path=top_file,
            reason="caller or callee performs unguarded filesystem read",
            score=0.88,
            evidence={"error_family": "FileNotFoundError"},
        ))

    if "modulenotfounderror" in text or "no module named" in text:
        causes.append(CausalNode(
            node_id="cause_dependency_boundary",
            kind="dependency_resolution_break",
            file_path=top_file,
            reason="dependency boundary is broken at import time",
            score=0.91,
            evidence={"error_family": "ModuleNotFoundError"},
        ))

    if "syntaxerror" in text or "indentationerror" in text:
        causes.append(CausalNode(
            node_id="cause_syntax_break",
            kind="syntax_break",
            file_path=top_file,
            reason="source module has invalid syntax or broken block structure",
            score=0.95,
            evidence={"error_family": "SyntaxError"},
        ))

    if "command not found" in text:
        causes.append(CausalNode(
            node_id="cause_shell_resolution",
            kind="shell_resolution_break",
            file_path=top_file,
            reason="shell executable cannot be resolved in environment",
            score=0.86,
            evidence={"error_family": "ShellCommandNotFound"},
        ))

    if not causes:
        causes.append(CausalNode(
            node_id="cause_generic_failure",
            kind="generic_failure",
            file_path=top_file,
            reason="generic unresolved failure surface",
            score=0.50,
            evidence={},
        ))

    return sorted(causes, key=lambda x: x.score, reverse=True)
''',

    "core/planner/repair_planner.py": r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class RepairPlan:
    plan_id: str
    hypothesis: str
    root_cause_nodes: list[str]
    target_files: list[str]
    edits: list[dict[str, Any]]
    expected_behavior: dict[str, Any]
    evidence: dict[str, Any]
    confidence: float
    risk: float
    blast_radius: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _make_runtime_file_plans(*, causes: list[dict[str, Any]], semantic: dict[str, Any] | None = None) -> list[RepairPlan]:
    plans: list[RepairPlan] = []
    localization_items = ((semantic or {}).get("localization") or {}).get("items") or []
    target_files: list[str] = []

    for item in localization_items:
        fp = item.get("file_path")
        if fp and fp not in target_files and str(fp).endswith(".py"):
            target_files.append(fp)

    if not target_files:
        return plans

    root_ids = [c["node_id"] for c in causes[:2]]

    for idx, target_file in enumerate(target_files[:3], start=1):
        src = _read_text(target_file)
        if 'read_text()' not in src:
            continue

        if 'Path("logs/app.log").read_text()' in src and '.exists()' not in src:
            guarded = src.replace(
                'Path("logs/app.log").read_text()',
                'Path("logs/app.log").read_text() if Path("logs/app.log").exists() else ""'
            )

            plans.append(RepairPlan(
                plan_id=f"plan_runtime_guard_{idx}",
                hypothesis="filesystem read invariant is broken in target module; guard the read and preserve safe output",
                root_cause_nodes=root_ids,
                target_files=[target_file],
                edits=[{
                    "file": target_file,
                    "kind": "replace_full",
                    "summary": "guard missing file read with exists fallback",
                    "candidate_code": guarded,
                }],
                expected_behavior={
                    "exception_absent": "FileNotFoundError",
                    "exit_code": 0,
                },
                evidence={
                    "strategy": "guard_exists",
                    "localization_target": target_file,
                },
                confidence=0.87,
                risk=0.12,
                blast_radius=0.12,
            ))

            wrapped = src.replace(
                'print(Path("logs/app.log").read_text())',
                'try:\\n    print(Path("logs/app.log").read_text())\\nexcept FileNotFoundError:\\n    print("")'
            )
            if wrapped != src:
                plans.append(RepairPlan(
                    plan_id=f"plan_runtime_recovery_{idx}",
                    hypothesis="runtime failure should be handled at boundary with explicit recovery",
                    root_cause_nodes=root_ids,
                    target_files=[target_file],
                    edits=[{
                        "file": target_file,
                        "kind": "replace_full",
                        "summary": "wrap file read with FileNotFoundError recovery",
                        "candidate_code": wrapped,
                    }],
                    expected_behavior={
                        "exception_absent": "FileNotFoundError",
                        "exit_code": 0,
                    },
                    evidence={
                        "strategy": "try_except_recovery",
                        "localization_target": target_file,
                    },
                    confidence=0.79,
                    risk=0.18,
                    blast_radius=0.18,
                ))

        plans.append(RepairPlan(
            plan_id=f"plan_runtime_operational_{idx}",
            hypothesis="missing path may be sufficient; create runtime file path without source edits",
            root_cause_nodes=root_ids,
            target_files=[target_file],
            edits=[{
                "file": target_file,
                "kind": "operational",
                "summary": "create logs/app.log path",
                "commands": ["mkdir -p logs", "touch logs/app.log"],
            }],
            expected_behavior={
                "exception_absent": "FileNotFoundError",
                "exit_code": 0,
            },
            evidence={
                "strategy": "touch_only",
                "localization_target": target_file,
            },
            confidence=0.66,
            risk=0.08,
            blast_radius=0.05,
        ))

    return plans


def _make_dependency_plans(*, causes: list[dict[str, Any]], semantic: dict[str, Any] | None = None) -> list[RepairPlan]:
    text = ((((semantic or {}).get("repro") or {}).get("stderr")) or "")
    pkg = ""
    marker = "No module named '"
    if marker in text:
        pkg = text.split(marker, 1)[1].split("'", 1)[0]

    if not pkg:
        return []

    target_file = ((semantic or {}).get("localization") or {}).get("top", {}).get("file_path", "") or ""
    root_ids = [c["node_id"] for c in causes[:1]]

    return [
        RepairPlan(
            plan_id="plan_dependency_install",
            hypothesis="dependency boundary can be restored by installing missing package",
            root_cause_nodes=root_ids,
            target_files=[target_file] if target_file else [],
            edits=[{
                "file": target_file,
                "kind": "operational",
                "summary": f"install missing dependency {pkg}",
                "commands": [f"pip install {pkg}"],
            }],
            expected_behavior={
                "exception_absent": "ModuleNotFoundError",
                "exit_code": 0,
            },
            evidence={"package": pkg, "strategy": "dependency_install"},
            confidence=0.78,
            risk=0.22,
            blast_radius=0.20,
        )
    ]


def build_repair_plans(*, error_text: str, semantic: dict[str, Any] | None, causes: list[dict[str, Any]], project_graph: dict[str, Any] | None) -> list[RepairPlan]:
    plans: list[RepairPlan] = []
    cause_kinds = {c["kind"] for c in causes}

    if "missing_runtime_file" in cause_kinds or "unsafe_io_boundary" in cause_kinds:
        plans.extend(_make_runtime_file_plans(causes=causes, semantic=semantic))

    if "dependency_resolution_break" in cause_kinds:
        plans.extend(_make_dependency_plans(causes=causes, semantic=semantic))

    return sorted(plans, key=lambda p: (p.confidence - p.risk - p.blast_radius), reverse=True)
''',

    "core/planner/branch_executor.py": r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import subprocess
import sys

from core.repro.project_workspace import build_temp_workspace
from core.verify.python_verify import verify_python


@dataclass
class BranchExecutionResult:
    ok: bool
    reason: str
    applied_files: list[str]
    workspace_root: str
    runtime: dict[str, Any]
    static_verify: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_repair_plan(plan: dict[str, Any], entry_file: str) -> dict[str, Any]:
    tmp, layout = build_temp_workspace(entry_file)
    try:
        workspace_root = Path(layout.workspace_root)
        applied_files: list[str] = []
        static_verify: dict[str, Any] | None = None

        for edit in plan.get("edits", []):
            target = edit.get("file")
            if not target:
                continue

            target_abs = Path(target).resolve()
            project_root = Path(layout.project_root)
            try:
                rel = target_abs.relative_to(project_root)
            except Exception:
                continue

            dst = workspace_root / rel

            if edit.get("kind") == "replace_full":
                code = edit.get("candidate_code", "") or ""
                dst.write_text(code, encoding="utf-8")
                applied_files.append(str(dst))
                static_verify = verify_python(code)

            elif edit.get("kind") == "operational":
                for cmd in edit.get("commands", []):
                    if cmd.startswith("mkdir -p "):
                        folder = cmd[len("mkdir -p "):].strip()
                        (workspace_root / folder).mkdir(parents=True, exist_ok=True)
                    elif cmd.startswith("touch "):
                        file_rel = cmd[len("touch "):].strip()
                        p = workspace_root / file_rel
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.touch()

        entry_abs = Path(entry_file).resolve()
        rel_entry = entry_abs.relative_to(Path(layout.project_root))
        runtime_proc = subprocess.run(
            [sys.executable, str(rel_entry)],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
        )

        runtime = {
            "ok": runtime_proc.returncode == 0,
            "returncode": runtime_proc.returncode,
            "stdout": runtime_proc.stdout or "",
            "stderr": runtime_proc.stderr or "",
        }

        ok = runtime["ok"] and (static_verify is None or static_verify.get("ok", False))
        reason = "plan branch execution passed" if ok else "plan branch execution failed"

        return BranchExecutionResult(
            ok=ok,
            reason=reason,
            applied_files=applied_files,
            workspace_root=str(workspace_root),
            runtime=runtime,
            static_verify=static_verify,
        ).to_dict()
    finally:
        tmp.cleanup()
''',

    "core/verify/contract_synth.py": r'''from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ContractSynthesisResult:
    ok: bool
    reason: str
    checks: list[dict[str, Any]]
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def synthesize_and_check_contract(*, before_error_text: str, branch_result: dict[str, Any], expected_behavior: dict[str, Any] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    expected_behavior = expected_behavior or {}

    runtime = branch_result.get("runtime", {}) or {}
    stderr = runtime.get("stderr", "") or ""
    returncode = runtime.get("returncode", 1)

    total = 0.0

    exc = expected_behavior.get("exception_absent")
    if exc:
        ok = exc not in stderr
        checks.append({
            "name": "exception_absent",
            "ok": ok,
            "expected": exc,
        })
        total += 0.5 if ok else 0.0

    expected_exit = expected_behavior.get("exit_code")
    if expected_exit is not None:
        ok = returncode == expected_exit
        checks.append({
            "name": "exit_code",
            "ok": ok,
            "expected": expected_exit,
            "actual": returncode,
        })
        total += 0.5 if ok else 0.0

    ok_all = all(x["ok"] for x in checks) if checks else False
    reason = "contract checks passed" if ok_all else "contract checks failed"

    return ContractSynthesisResult(
        ok=ok_all,
        reason=reason,
        checks=checks,
        score=round(total, 4),
    ).to_dict()
''',

    "planner_probe.py": r'''#!/usr/bin/env python3

import json

from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.branch_executor import execute_repair_plan
from core.verify.contract_synth import synthesize_and_check_contract
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.repro.harness import run_python_file


def main():
    file_path = "demo/cross_file_dep.py"
    repro = run_python_file(file_path).to_dict()
    semantic = {
        "repro": repro,
        "localization": summarize_suspicions(localize_fault(repro.get("stderr", ""), file_path=file_path)),
    }
    graph = build_project_graph(file_path).to_dict()
    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=repro.get("stderr", ""),
        semantic=semantic,
        project_graph=graph,
    )]
    plans = [p.to_dict() for p in build_repair_plans(
        error_text=repro.get("stderr", ""),
        semantic=semantic,
        causes=causes,
        project_graph=graph,
    )]

    best_plan = plans[0] if plans else None
    branch = execute_repair_plan(best_plan, file_path) if best_plan else None
    contract = synthesize_and_check_contract(
        before_error_text=repro.get("stderr", ""),
        branch_result=branch or {},
        expected_behavior=(best_plan or {}).get("expected_behavior", {}),
    ) if best_plan else None

    print(json.dumps({
        "graph_summary": {
            "project_root": graph.get("project_root"),
            "file_count": len(graph.get("files", [])),
        },
        "causes": causes,
        "plan_count": len(plans),
        "best_plan": best_plan,
        "branch_result": branch,
        "contract_result": contract,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
''',

    "core/autofix.py": r'''from __future__ import annotations

from typing import Any
import ast
import re

from core.engine.context_builder import build_context
from core.engine.orchestrator import Orchestrator
from core.engine.router import PolicyRouter
from core.verify.sandbox import VerifierHub, run_in_sandbox
from core.verify.python_verify import verify_python
from core.verify.behavioral_verify import verify_python_runtime, verify_repro_delta
from core.memory import event_store, retrieval
from core.util.patch_apply import make_backup, apply_text_replacement, restore_backup
from core.util.safe_exec import execute_safe_suggestions
from core.repro.harness import run_python_file, run_shell_text
from core.semantic.fault_localizer import localize_fault, summarize_suspicions
from core.testsynth.replay_test import run_python_replay
from core.testsynth.regression_guard import (
    check_failure_signature_removed,
    check_expected_exception_absent,
    combine_regression_guards,
)
from core.project.graph import build_project_graph
from core.causal.analyzer import analyze_failure_causes
from core.planner.repair_planner import build_repair_plans
from core.planner.branch_executor import execute_repair_plan
from core.verify.contract_synth import synthesize_and_check_contract

from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert
from core.experts.file_runtime import FileRuntimeExpert


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


class RankerAdapter:
    def _score(self, candidate):
        if isinstance(candidate, dict):
            base = float(candidate.get("confidence", 0.0) or 0.0)
            repro_fix = float(candidate.get("repro_fix_score", 0.0) or 0.0)
            regression = float(candidate.get("regression_score", 0.0) or 0.0)
            synthesized = float(candidate.get("synth_test_score", 0.0) or 0.0)
            prior = float(candidate.get("historical_success_prior", 0.0) or 0.0)
            blast_radius = float(candidate.get("blast_radius", 0.0) or 0.0)
            sandbox_bonus = 0.10 if ((candidate.get("sandbox") or {}).get("ok") is True) else 0.0
            return base + repro_fix + regression + synthesized + prior + sandbox_bonus - blast_radius
        return getattr(candidate, "confidence", 0.0)

    def rank(self, candidates, context=None):
        if not isinstance(candidates, list):
            return candidates
        return sorted(candidates, key=self._score, reverse=True)


class ExpertAdapter:
    def __init__(self):
        self._registry = {
            "python_syntax": PythonSyntaxExpert(),
            "dependency": DependencyExpert(),
            "shell_runtime": ShellRuntimeExpert(),
            "memory_retrieval": MemoryRetrievalExpert(),
            "llm_fallback": LLMFallbackExpert(),
            "file_runtime": FileRuntimeExpert(),
        }

    def get(self, name: str):
        return self._registry[name]


def _build_orchestrator() -> Orchestrator:
    return Orchestrator(
        router=PolicyRouter(),
        experts=ExpertAdapter(),
        verifier=VerifierHub(),
        ranker=RankerAdapter(),
        store=EventStoreAdapter(),
    )


def _extract_field(text: str, field: str):
    patterns = [
        rf"{field}='((?:[^'\\\\]|\\\\.)*)'",
        rf'{field}="((?:[^"\\\\]|\\\\.)*)"',
        rf"{field}=([0-9]+(?:\.[0-9]+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            raw = m.group(1)
            try:
                return ast.literal_eval(f"'{raw}'")
            except Exception:
                try:
                    return float(raw) if "." in raw or raw.isdigit() else raw
                except Exception:
                    return raw
    return None


def _normalize_candidate(candidate):
    if isinstance(candidate, dict):
        c = dict(candidate)
        c.setdefault("kind", "")
        c.setdefault("confidence", 0.0)
        c.setdefault("candidate_code", "")
        c.setdefault("metadata", {})
        c.setdefault("repro_fix_score", 0.0)
        c.setdefault("regression_score", 0.0)
        c.setdefault("synth_test_score", 0.0)
        c.setdefault("historical_success_prior", 0.0)
        c.setdefault("blast_radius", 0.0)
        c.setdefault("hypothesis", "")
        c.setdefault("semantic_claim", "")
        c.setdefault("affected_scope", [])
        c.setdefault("target_file", c.get("file_path_hint"))
        patch = c.get("patch")
        if c["kind"] == "" and isinstance(patch, str) and patch.startswith("pip install "):
            c["kind"] = "dependency_install"
        elif c["kind"] == "" and c.get("expert") == "file_runtime":
            c["kind"] = "runtime_file_missing"
        return c

    attrs = {}
    for name in (
        "expert_name",
        "kind",
        "patched_code",
        "patch_unified_diff",
        "rationale",
        "router_score",
        "expert_score",
        "memory_prior",
        "patch_safety_score",
        "metadata",
    ):
        if hasattr(candidate, name):
            attrs[name] = getattr(candidate, name)

    if attrs:
        return {
            "expert": attrs.get("expert_name", "unknown"),
            "kind": attrs.get("kind", ""),
            "confidence": attrs.get("expert_score", 0.0),
            "summary": attrs.get("rationale", ""),
            "patch": attrs.get("patch_unified_diff"),
            "candidate_code": attrs.get("patched_code", "") or "",
            "raw_candidate": str(candidate),
            "metadata": attrs.get("metadata", {}) or {},
            "router_score": attrs.get("router_score", 0.0),
            "expert_score": attrs.get("expert_score", 0.0),
            "memory_prior": attrs.get("memory_prior", 0.0),
            "patch_safety_score": attrs.get("patch_safety_score", 0.0),
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "synth_test_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
            "target_file": None,
        }

    text = str(candidate)
    if "RepairCandidate(" in text:
        return {
            "expert": _extract_field(text, "expert_name") or "python_syntax",
            "kind": _extract_field(text, "kind") or "python_patch",
            "confidence": _extract_field(text, "expert_score") or 0.0,
            "summary": _extract_field(text, "rationale") or text,
            "patch": _extract_field(text, "patch_unified_diff"),
            "candidate_code": _extract_field(text, "patched_code") or "",
            "raw_candidate": text,
            "metadata": {},
            "router_score": _extract_field(text, "router_score") or 0.0,
            "expert_score": _extract_field(text, "expert_score") or 0.0,
            "memory_prior": _extract_field(text, "memory_prior") or 0.0,
            "patch_safety_score": _extract_field(text, "patch_safety_score") or 0.0,
            "repro_fix_score": 0.0,
            "regression_score": 0.0,
            "synth_test_score": 0.0,
            "historical_success_prior": 0.0,
            "blast_radius": 0.0,
            "hypothesis": "",
            "semantic_claim": "",
            "affected_scope": [],
            "target_file": None,
        }

    return {
        "expert": "unknown",
        "kind": "unknown",
        "confidence": 0.0,
        "summary": text,
        "patch": None,
        "candidate_code": "",
        "raw_candidate": text,
        "metadata": {},
        "repro_fix_score": 0.0,
        "regression_score": 0.0,
        "synth_test_score": 0.0,
        "historical_success_prior": 0.0,
        "blast_radius": 0.0,
        "hypothesis": "",
        "semantic_claim": "",
        "affected_scope": [],
        "target_file": None,
    }


def _normalize_candidates(candidates):
    if not isinstance(candidates, list):
        return candidates
    return [_normalize_candidate(c) for c in candidates]


def _build_semantic_prelude(error_text: str, file_path: str | None):
    if file_path and str(file_path).endswith(".py"):
        repro = run_python_file(file_path)
        suspicions = localize_fault(repro.stderr or error_text, file_path=file_path)
        return {
            "repro": repro.to_dict(),
            "localization": summarize_suspicions(suspicions),
        }

    repro = run_shell_text(error_text)
    suspicions = localize_fault(error_text, file_path=file_path)
    return {
        "repro": repro.to_dict(),
        "localization": summarize_suspicions(suspicions),
    }


def _build_repair_planner_prelude(error_text: str, file_path: str | None, semantic: dict[str, Any] | None):
    graph = build_project_graph(file_path).to_dict() if file_path else {"project_root": str("."), "files": [], "adjacency": {}}
    causes = [c.to_dict() for c in analyze_failure_causes(
        error_text=error_text,
        semantic=semantic,
        project_graph=graph,
    )]
    plans = [p.to_dict() for p in build_repair_plans(
        error_text=error_text,
        semantic=semantic,
        causes=causes,
        project_graph=graph,
    )]
    best_plan = plans[0] if plans else None
    branch_result = execute_repair_plan(best_plan, file_path) if best_plan and file_path else None
    contract_result = synthesize_and_check_contract(
        before_error_text=error_text,
        branch_result=branch_result or {},
        expected_behavior=(best_plan or {}).get("expected_behavior", {}),
    ) if best_plan else None

    return {
        "project_graph": graph,
        "causes": causes,
        "repair_plans": plans,
        "best_plan": best_plan,
        "branch_result": branch_result,
        "contract_result": contract_result,
    }


def _verify_candidate(candidate, context=None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""
    patch = c.get("patch", None)

    if kind in {"python_patch", "syntax"} and isinstance(code, str) and code.strip():
        return verify_python(code)

    if kind in {"dependency_install", "dependency"} or (
        isinstance(patch, str) and patch.strip().startswith("pip install ")
    ):
        return {"ok": True, "reason": "dependency install suggestion accepted as non-python command candidate", "mode": "dependency_install"}

    if kind == "runtime_file_missing":
        target_file = c.get("target_file") or getattr(context, "file_path", "")
        if target_file and str(target_file).endswith(".py"):
            if isinstance(code, str) and code.strip():
                py = verify_python(code)
                py["mode"] = kind
                py["reason"] = f"operational fix with python payload validation: {py.get('reason', '')}"
                return py
        return {"ok": True, "reason": "operational file fix for non-python target; skipped python syntax verification", "mode": kind}

    if kind in {"shell_command", "shell_runtime", "shell_command_missing", "shell_permission_denied", "shell_missing_path"}:
        return {"ok": True, "reason": "non-python operational fix; skipped python syntax verification", "mode": kind or "operational"}

    if isinstance(code, str) and code.strip():
        return verify_python(code)

    return {"ok": True, "reason": "no code payload"}


def _apply_candidate(candidate, file_path: str | None):
    c = _normalize_candidate(candidate)
    target_file = c.get("target_file") or file_path
    if not target_file:
        return {"applied": False, "reason": "no file_path provided", "backup_path": None}

    kind = c.get("kind", "") or ""
    code = c.get("candidate_code", "") or ""

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"applied": False, "reason": f"candidate kind not auto-applicable: {kind or 'unknown'}", "backup_path": None}

    if not isinstance(code, str) or not code.strip():
        return {"applied": False, "reason": "candidate_code empty", "backup_path": None}

    backup = make_backup(target_file)
    apply_text_replacement(target_file, code)

    verify_result = verify_python(code)
    if not verify_result.get("ok", False):
        restore_backup(target_file, backup)
        return {
            "applied": False,
            "reason": "post-apply verification failed; restored backup",
            "backup_path": str(backup),
            "verify": verify_result,
        }

    return {
        "applied": True,
        "reason": "patch applied and verified",
        "backup_path": str(backup),
        "verify": verify_result,
        "target_file": target_file,
    }


def _execute_candidate(candidate, *, dry_run: bool = False, cwd: str | None = None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    metadata = c.get("metadata", {}) or {}
    patch = c.get("patch", None)

    if kind not in {"shell_command_missing", "shell_permission_denied", "shell_missing_path", "runtime_file_missing"}:
        return {"executed": False, "reason": f"candidate kind not executable: {kind or 'unknown'}", "results": []}

    command_text = patch
    if not command_text:
        suggestions = metadata.get("suggestions", [])
        if kind == "shell_command_missing":
            command_text = " && ".join(suggestions[:3]) if suggestions else None
        elif kind == "shell_permission_denied":
            command_text = " && ".join(suggestions[:2]) if suggestions else patch
        elif kind in {"shell_missing_path", "runtime_file_missing"}:
            command_text = " && ".join([s for s in suggestions if s.startswith(("mkdir -p", "touch", "chmod +x"))])

    return execute_safe_suggestions(command_text, dry_run=dry_run, cwd=cwd)


def _behavioral_verify_for_candidate(candidate, file_path: str | None, semantic_before: dict[str, Any] | None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    target_file = c.get("target_file") or file_path

    if not target_file or not str(target_file).endswith(".py"):
        return {"ok": True, "mode": "behavioral_skip", "reason": "non-python target; behavioral runtime verify skipped"}

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"ok": True, "mode": "behavioral_skip", "reason": f"candidate kind not behaviorally executed: {kind or 'unknown'}"}

    code = c.get("candidate_code", "") or ""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "mode": "behavioral_skip", "reason": "candidate_code empty"}

    before_stderr = (((semantic_before or {}).get("repro") or {}).get("stderr", "")) if isinstance(semantic_before, dict) else ""
    before_exception_type = (((semantic_before or {}).get("repro") or {}).get("exception_type", "")) if isinstance(semantic_before, dict) else ""

    backup = make_backup(target_file)
    try:
        apply_text_replacement(target_file, code)
        runtime = verify_python_runtime(target_file).to_dict()
        delta = verify_repro_delta(before_stderr, runtime.get("stderr", "")).to_dict()

        ok = bool(runtime.get("ok", False)) or bool(delta.get("ok", False))
        return {
            "ok": ok,
            "mode": "behavioral_verify",
            "reason": "behavioral verification completed",
            "runtime": runtime,
            "delta": delta,
            "before_exception_type": before_exception_type,
            "repro_fix_score": 0.75 if delta.get("ok", False) else 0.0,
            "regression_score": 0.65 if runtime.get("ok", False) else 0.0,
        }
    finally:
        restore_backup(target_file, backup)


def _synthesized_regression_tests(candidate, file_path: str | None, semantic_before: dict[str, Any] | None):
    c = _normalize_candidate(candidate)
    kind = c.get("kind", "") or ""
    target_file = c.get("target_file") or file_path

    if not target_file or not str(target_file).endswith(".py"):
        return {"ok": True, "mode": "synth_skip", "reason": "non-python target; synthesized tests skipped", "score": 0.0}

    if kind not in {"syntax", "python_patch", "runtime_file_missing"}:
        return {"ok": True, "mode": "synth_skip", "reason": f"candidate kind not synthesized-tested: {kind or 'unknown'}", "score": 0.0}

    code = c.get("candidate_code", "") or ""
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "mode": "synth_skip", "reason": "candidate_code empty", "score": 0.0}

    before_stderr = (((semantic_before or {}).get("repro") or {}).get("stderr", "")) if isinstance(semantic_before, dict) else ""
    before_exception_type = (((semantic_before or {}).get("repro") or {}).get("exception_type", "")) if isinstance(semantic_before, dict) else ""

    replay = run_python_replay(file_path=target_file, candidate_code=code, target_file=target_file).to_dict()
    guard1_obj = check_failure_signature_removed(before_stderr, replay.get("stderr", ""))
    guard2_obj = check_expected_exception_absent(before_exception_type, replay.get("stderr", ""))
    combined = combine_regression_guards(guard1_obj, guard2_obj).to_dict()

    return {
        "ok": bool(combined.get("ok", False)),
        "mode": "synthesized_regression",
        "reason": "synthesized replay and regression guards evaluated",
        "score": float(combined.get("score", 0.0) or 0.0),
        "replay": replay,
        "guards": {
            "failure_signature_removed": guard1_obj.to_dict(),
            "exception_absent": guard2_obj.to_dict(),
            "combined": combined,
        },
    }


def _evaluate_candidates(candidates, *, file_path: str | None, semantic: dict[str, Any] | None):
    normalized = _normalize_candidates(candidates)
    enriched = []

    for cand in normalized:
        bv = _behavioral_verify_for_candidate(cand, file_path, semantic)
        cand2 = dict(cand)
        cand2["behavioral_verify"] = bv
        cand2["repro_fix_score"] = float(bv.get("repro_fix_score", 0.0) or 0.0)
        cand2["regression_score"] = float(bv.get("regression_score", 0.0) or 0.0)

        synth = _synthesized_regression_tests(cand2, file_path, semantic)
        cand2["synthesized_tests"] = synth
        cand2["synth_test_score"] = float(synth.get("score", 0.0) or 0.0)

        cand2["historical_success_prior"] = float(retrieval.candidate_history_prior(cand2) or 0.0)

        strategy = ((cand2.get("metadata") or {}).get("strategy", "")) if isinstance(cand2.get("metadata"), dict) else ""
        if strategy == "touch_only":
            cand2["blast_radius"] = 0.05
        elif strategy == "guard_exists":
            cand2["blast_radius"] = 0.12
        elif strategy == "try_except_recovery":
            cand2["blast_radius"] = 0.18
        else:
            cand2["blast_radius"] = float(cand2.get("blast_radius", 0.0) or 0.0)

        sandbox_context = build_context(error_text="", file_path=cand2.get("target_file") or file_path)
        cand2["sandbox"] = run_in_sandbox(cand2, sandbox_context)

        enriched.append(cand2)

    ranked = RankerAdapter().rank(enriched)
    best = ranked[0] if ranked else None
    return enriched, best


def _fallback_pipeline(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False, semantic: dict[str, Any] | None = None, planner: dict[str, Any] | None = None):
    context = build_context(error_text=error_text, file_path=file_path)
    try:
        setattr(context, "semantic", semantic)
    except Exception:
        pass

    routes = PolicyRouter().route(context)

    candidates = []
    registry = ExpertAdapter()
    for route_name in routes:
        expert = registry.get(route_name)
        if hasattr(expert, "propose"):
            try:
                proposals = expert.propose(context)
                if isinstance(proposals, list):
                    candidates.extend(proposals)
                elif proposals is not None:
                    candidates.append(proposals)
            except Exception as e:
                candidates.append({
                    "expert": route_name,
                    "kind": "expert_failure",
                    "confidence": 0.0,
                    "summary": f"expert failure: {type(e).__name__}: {e}",
                    "patch": None,
                    "candidate_code": "",
                })

    enriched, best = _evaluate_candidates(candidates, file_path=file_path, semantic=semantic)

    verify_result = _verify_candidate(best, context=context)
    sandbox_result = (best or {}).get("sandbox") if isinstance(best, dict) else None
    apply_result = _apply_candidate(best, file_path=file_path) if auto_apply and best is not None else None
    exec_result = _execute_candidate(best, dry_run=dry_run) if exec_suggestions and best is not None else None
    behavioral_verify = (best or {}).get("behavioral_verify") if isinstance(best, dict) else None
    synthesized_tests = (best or {}).get("synthesized_tests") if isinstance(best, dict) else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "planner": planner,
        "routes": routes,
        "candidates": enriched,
        "best": _normalize_candidate(best) if best is not None else None,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }
    EventStoreAdapter().append_event(payload)

    return {
        "result": _normalize_candidate(best) if best is not None else None,
        "semantic": semantic,
        "planner": planner,
        "routes": routes,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }


def run_autofix(error_text: str, file_path: str | None = None, auto_apply: bool = False, exec_suggestions: bool = False, dry_run: bool = False):
    semantic = _build_semantic_prelude(error_text=error_text, file_path=file_path)
    planner = _build_repair_planner_prelude(error_text=error_text, file_path=file_path, semantic=semantic)

    context = build_context(error_text=error_text, file_path=file_path)
    try:
        setattr(context, "semantic", semantic)
    except Exception:
        pass

    try:
        result = _build_orchestrator().run(context)
    except Exception:
        return _fallback_pipeline(
            error_text=error_text,
            file_path=file_path,
            auto_apply=auto_apply,
            exec_suggestions=exec_suggestions,
            dry_run=dry_run,
            semantic=semantic,
            planner=planner,
        )

    candidates = result if isinstance(result, list) else [result]
    enriched, best = _evaluate_candidates(candidates, file_path=file_path, semantic=semantic)

    verify_result = _verify_candidate(best, context=context)
    behavioral_verify = (best or {}).get("behavioral_verify") if isinstance(best, dict) else None
    synthesized_tests = (best or {}).get("synthesized_tests") if isinstance(best, dict) else None
    sandbox_result = (best or {}).get("sandbox") if isinstance(best, dict) else None
    apply_result = _apply_candidate(best, file_path=file_path) if auto_apply and best is not None else None
    exec_result = _execute_candidate(best, dry_run=dry_run) if exec_suggestions and best is not None else None

    payload = {
        "error_text": error_text,
        "file_path": file_path,
        "semantic": semantic,
        "planner": planner,
        "result": _normalize_candidate(best) if best is not None else None,
        "candidates": enriched,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
    }
    EventStoreAdapter().append_event(payload)

    return {
        "result": _normalize_candidate(best) if best is not None else None,
        "semantic": semantic,
        "planner": planner,
        "verify": verify_result,
        "behavioral_verify": behavioral_verify,
        "synthesized_tests": synthesized_tests,
        "sandbox": sandbox_result,
        "apply": apply_result,
        "exec": exec_result,
        "candidate_count": len(enriched),
        "candidates": enriched,
    }
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
