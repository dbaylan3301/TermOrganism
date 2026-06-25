from __future__ import annotations
from unittest.mock import patch
from core.repair.engine import repair

@patch("core.repair.engine.EventStoreAdapter")
@patch("core.repair.engine.apply_hot_cache_to_payload", side_effect=lambda p, **kw: p)
@patch("core.repair.engine.build_semantic_prelude", return_value={"repro": {}, "localization": {}})
@patch("core.repair.engine.build_candidates", return_value=[])
@patch("core.repair.engine.build_and_rank_plans", return_value=[])
def test_repair_returns_ok_false_on_no_plans(mock_plans, mock_candidates, mock_prelude, mock_hot, mock_event):
    result = repair("error", None)
    assert result["ok"] is False
    assert result["ranked_plans"] == []