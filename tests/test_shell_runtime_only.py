#!/usr/bin/env python3
from core.engine.context_builder import build_context
from core.experts.shell_runtime import ShellRuntimeExpert

expert = ShellRuntimeExpert()

cases = [
    "zsh: command not found: bat",
    "bash: rg: command not found",
    "Permission denied: ./run.sh",
    "ls: cannot access 'logs/app.log': No such file or directory",
]

for error_text in cases:
    ctx = build_context(error_text=error_text)
    out = expert.propose(ctx)
    print("=" * 72)
    print(error_text)
    print(out)
