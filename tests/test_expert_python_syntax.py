from __future__ import annotations
from core.models.schemas import FailureContext
from core.experts.python_syntax import PythonSyntaxExpert

def test_python_syntax_expert_has_name():
    expert = PythonSyntaxExpert()
    assert expert.name

def test_python_syntax_expert_propose_returns_list():
    expert = PythonSyntaxExpert()
    ctx = FailureContext(error_text="SyntaxError: invalid syntax")
    result = expert.propose(ctx)
    assert isinstance(result, list)