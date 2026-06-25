from __future__ import annotations
from core.repair.utils import force_plan_target_to_file, resolve_semantic_target

def test_force_plan_target_to_file_sets_target():
    plan = {"target_files": [], "edits": [{"file": None}]}
    result = force_plan_target_to_file(plan, "/tmp/test.py")
    assert result["target_files"] == ["/tmp/test.py"]
    assert result["edits"][0]["file"] == "/tmp/test.py"

def test_force_plan_target_to_file_no_change_with_valid_target():
    plan = {"target_files": ["/tmp/other.py"]}
    result = force_plan_target_to_file(plan, "/tmp/test.py")
    assert result["target_files"] == ["/tmp/other.py"]

def test_resolve_semantic_target_returns_file_path():
    semantic = {"localization": {"top": {"file_path": "/tmp/test.py"}}}
    result = resolve_semantic_target("/tmp/other.py", semantic)
    assert result == "/tmp/test.py"

def test_resolve_semantic_target_returns_original_when_no_semantic():
    result = resolve_semantic_target("/tmp/test.py", None)
    assert result == "/tmp/test.py"

def test_resolve_semantic_target_skips_stdlib():
    semantic = {"localization": {"top": {"file_path": "/usr/lib/python3.10/os.py"}}}
    result = resolve_semantic_target("/tmp/test.py", semantic)
    assert result == "/tmp/test.py"