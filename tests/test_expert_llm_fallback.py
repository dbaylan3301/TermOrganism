from __future__ import annotations
from core.models.schemas import FailureContext
from core.experts.llm_fallback import LLMFallbackExpert

def test_llm_fallback_expert_has_name():
    expert = LLMFallbackExpert()
    assert expert.name

def test_llm_fallback_expert_propose_returns_list():
    expert = LLMFallbackExpert()
    ctx = FailureContext(error_text="some error")
    result = expert.propose(ctx)
    assert isinstance(result, list)