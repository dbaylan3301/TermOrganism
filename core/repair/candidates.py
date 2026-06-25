from __future__ import annotations

from pathlib import Path
from typing import Any

from core.experts.file_runtime import FileRuntimeExpert
from core.experts.python_syntax import PythonSyntaxExpert
from core.experts.dependency import DependencyExpert
from core.experts.shell_runtime import ShellRuntimeExpert
from core.experts.memory_retrieval import MemoryRetrievalExpert
from core.experts.llm_fallback import LLMFallbackExpert

from .events import emit_thought
from .utils import resolve_semantic_target


def build_candidates(
    error_text: str,
    file_path: str | None,
    semantic: dict[str, Any] | None = None,
    thought_bus: Any = None,
) -> list[dict[str, Any]]:
    semantic_target = resolve_semantic_target(file_path, semantic)

    ctx = type("Ctx", (), {})()
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

    emit_thought(
        thought_bus,
        "Candidate Generation",
        f"{len(candidates)} candidates produced",
        kind="info",
    )

    expert_names = sorted({
        str((c or {}).get("expert") or "unknown")
        for c in candidates
        if isinstance(c, dict)
    })
    emit_thought(
        thought_bus,
        "Expert Routing",
        "experts=" + ", ".join(expert_names),
        kind="info",
    )

    for cand in list(candidates)[:3]:
        if isinstance(cand, dict):
            emit_thought(
                thought_bus,
                "Hypothesis Generation",
                str(
                    cand.get("summary")
                    or cand.get("semantic_claim")
                    or cand.get("hypothesis")
                    or "candidate proposed"
                ),
                kind="info",
                confidence=cand.get("confidence"),
                file_path=cand.get("target_file") or cand.get("file_path_hint"),
            )

    return candidates
