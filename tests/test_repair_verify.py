from __future__ import annotations
from core.repair.verify import verify_repair

def test_verify_repair_no_file():
    result = verify_repair({}, None, "error")
    assert result["ok"] is False
    assert "no file" in result["reason"]

def test_verify_repair_no_edits():
    result = verify_repair({"edits": []}, "/tmp/test.py", "error")
    assert result["ok"] is False