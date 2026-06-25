from __future__ import annotations
from core.models.schemas import FailureContext
from core.experts.memory_retrieval import MemoryRetrievalExpert

def test_memory_retrieval_expert_has_name():
    expert = MemoryRetrievalExpert()
    assert expert.name

def test_memory_retrieval_expert_propose_returns_list():
    expert = MemoryRetrievalExpert()
    ctx = FailureContext(error_text="some error")
    result = expert.propose(ctx)
    assert isinstance(result, list)