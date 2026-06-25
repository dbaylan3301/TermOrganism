from __future__ import annotations
from unittest.mock import patch
from core.repair.planner import build_and_rank_plans

@patch("core.repair.planner.build_repair_plans", return_value=[])
@patch("core.repair.planner.expand_multifile_plan_family", return_value=[])
@patch("core.repair.planner.rank_plans", return_value=[])
def test_build_and_rank_plans_empty(mock_rank, mock_expand, mock_build):
    result = build_and_rank_plans("error", None, [], {}, [], None)
    assert result == []
    mock_build.assert_called_once()