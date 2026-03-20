#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()

PATCHES = {
    "core/engine/router.py": '''from __future__ import annotations


class PolicyRouter:
    def route(self, context):
        error_text = (getattr(context, "error_text", "") or "").lower()
        semantic = getattr(context, "semantic", {}) or {}

        repro = semantic.get("repro", {}) if isinstance(semantic, dict) else {}
        localization = semantic.get("localization", {}) if isinstance(semantic, dict) else {}
        top = localization.get("top", {}) if isinstance(localization, dict) else {}

        exception_type = (repro.get("exception_type", "") or "").lower()
        reason = (top.get("reason", "") or "").lower()
        score = float(top.get("score", 0.0) or 0.0)

        experts: list[str] = []

        # semantic-first routing
        if exception_type in {"syntaxerror", "indentationerror"} or "syntax failure" in reason:
            experts.append("python_syntax")

        if exception_type == "modulenotfounderror" or "dependency/import failure" in reason:
            experts.append("dependency")

        if exception_type == "filenotfounderror" or "runtime path/file access failure" in reason:
            experts.append("file_runtime")

        if exception_type == "shellerror" or "shell executable resolution failure" in reason:
            experts.append("shell_runtime")

        if "permission boundary failure" in reason:
            experts.append("shell_runtime")

        # fallback to text-based routing if semantic signal is weak
        if not experts or score < 0.60:
            if "syntaxerror" in error_text or "indentationerror" in error_text:
                if "python_syntax" not in experts:
                    experts.append("python_syntax")

            if "modulenotfounderror" in error_text or "no module named" in error_text:
                if "dependency" not in experts:
                    experts.append("dependency")

            if "filenotfounderror" in error_text or "no such file or directory" in error_text:
                if "file_runtime" not in experts:
                    experts.append("file_runtime")

            if (
                "permission denied" in error_text
                or "command not found" in error_text
                or "not found" in error_text
            ) and "no such file or directory" not in error_text:
                if "shell_runtime" not in experts:
                    experts.append("shell_runtime")

        if not experts:
            experts.append("memory_retrieval")
            experts.append("llm_fallback")

        return experts


def route(context):
    return PolicyRouter().route(context)
''',

    "test_semantic_router.py": '''#!/usr/bin/env python3
from core.engine.context_builder import build_context
from core.engine.router import PolicyRouter

router = PolicyRouter()

cases = [
    (
        "dependency semantic",
        build_context("ModuleNotFoundError: No module named 'x'"),
        {
            "repro": {"exception_type": "ModuleNotFoundError", "reproduced": True},
            "localization": {
                "top": {
                    "reason": "dependency/import failure at module import boundary",
                    "score": 0.84,
                }
            },
        },
    ),
    (
        "runtime semantic",
        build_context("FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'"),
        {
            "repro": {"exception_type": "FileNotFoundError", "reproduced": True},
            "localization": {
                "top": {
                    "reason": "runtime path/file access failure",
                    "score": 0.82,
                }
            },
        },
    ),
    (
        "shell semantic",
        build_context("zsh: command not found: bat"),
        {
            "repro": {"exception_type": "ShellError", "reproduced": True},
            "localization": {
                "top": {
                    "reason": "shell executable resolution failure",
                    "score": 0.76,
                }
            },
        },
    ),
]

for name, ctx, semantic in cases:
    setattr(ctx, "semantic", semantic)
    print(name, "->", router.route(ctx))
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
