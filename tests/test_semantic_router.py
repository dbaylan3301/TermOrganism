#!/usr/bin/env python3
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
