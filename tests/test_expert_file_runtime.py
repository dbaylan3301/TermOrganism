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