from __future__ import annotations

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
