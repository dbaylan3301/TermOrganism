from __future__ import annotations

from core.autofix import run_autofix


def test_cross_file_repair_returns_result():
    error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""
    result = run_autofix(
        error_text=error_text,
        file_path="demo/cross_file_dep.py",
    )
    assert result is not None
    assert "best_plan" in result or "ranked_plans" in result


def test_cross_file_repair_plan_evidence():
    error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""
    result = run_autofix(
        error_text=error_text,
        file_path="demo/cross_file_dep.py",
    )
    best = result.get("best_plan") or {}
    ev = best.get("evidence") or {}

    assert best.get("plan_id") is not None
    assert ev.get("strategy") is not None
    assert ev.get("provider") is not None
    assert ev.get("caller") is not None
    assert isinstance(best.get("target_files"), list)


def test_cross_file_repair_result_is_dict():
    error_text = """Traceback (most recent call last):
  File "/root/TermOrganismGitFork/demo/cross_file_dep.py", line 3, in <module>
    print(read_log())
          ~~~~~~~~^^
  File "/root/TermOrganismGitFork/demo/helper_mod.py", line 4, in read_log
    return Path("logs/app.log").read_text()
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
FileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'
"""
    result = run_autofix(
        error_text=error_text,
        file_path="demo/cross_file_dep.py",
    )
    assert isinstance(result, dict)
    assert "ok" in result
