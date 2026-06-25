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