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