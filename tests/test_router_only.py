#!/usr/bin/env python3
from core.engine.context_builder import build_context
from core.engine.router import PolicyRouter

router = PolicyRouter()

cases = [
    ("SyntaxError: expected ':'", "python_syntax"),
    ("ModuleNotFoundError: No module named 'foo'", "dependency"),
    ("bash: abc: command not found", "shell_runtime"),
]

for error_text, expected in cases:
    ctx = build_context(error_text=error_text)
    routed = router.route(ctx)
    ok = expected in routed
    print(f"{expected=}, {routed=}, ok={ok}")
