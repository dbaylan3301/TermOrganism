from __future__ import annotations
from core.repair.candidates import build_candidates

def test_build_candidates_returns_list():
    result = build_candidates("error", None, None)
    assert isinstance(result, list)

def test_build_candidates_with_file():
    result = build_candidates("error", "/tmp/nonexistent.py", None)
    assert isinstance(result, list)