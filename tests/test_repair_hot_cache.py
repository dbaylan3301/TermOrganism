from __future__ import annotations
from unittest.mock import patch, MagicMock
from core.repair.hot_cache import boost_confidence, attach_hot_cache_boost, apply_hot_cache_to_payload

@patch("core.memory.engine.MemoryEngine")
def test_boost_confidence_returns_base_when_no_cache(mock_engine):
    mock_engine.return_value.find_similar.return_value = []
    result = boost_confidence(0.5, "some error")
    assert "confidence" in result
    assert result["recommendation"] in ("auto_apply", "apply_with_review", "human_review")

@patch("core.memory.engine.MemoryEngine")
def test_attach_hot_cache_boost_adds_memory(mock_engine):
    mock_engine.return_value.find_similar.return_value = []
    payload = {"confidence": {"score": 0.5}}
    result = attach_hot_cache_boost(payload, error_text="test error")
    assert "memory" in result
    assert "hot_cache" in result["memory"]

@patch("core.memory.engine.MemoryEngine")
def test_apply_hot_cache_to_payload_structure(mock_engine):
    mock_engine.return_value.find_similar.return_value = []
    payload = {"confidence": {"score": 0.5}}
    result = apply_hot_cache_to_payload(payload, error_text="test error")
    assert "memory" in result
    assert "hot_cache" in result["memory"]