from __future__ import annotations

from core.autofix import run_autofix


def test_multifile_result_shape():
    result = run_autofix(
        error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
        file_path="demo/cross_file_dep.py",
    )
    assert isinstance(result, dict)
    assert "ok" in result


def test_multifile_best_plan():
    result = run_autofix(
        error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
        file_path="demo/cross_file_dep.py",
    )
    best = result.get("best_plan") or {}
    assert best.get("plan_id") is not None
    assert isinstance(best.get("target_files"), list)


def test_multifile_evidence():
    result = run_autofix(
        error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
        file_path="demo/cross_file_dep.py",
    )
    best = result.get("best_plan") or {}
    ev = best.get("evidence") or {}
    assert ev.get("provider") is not None
    assert ev.get("caller") is not None


def test_multifile_result_has_required_fields():
    result = run_autofix(
        error_text="Traceback (most recent call last):\n  File \"/root/TermOrganismGitFork/demo/cross_file_dep.py\", line 3, in <module>\n    print(read_log())\n  File \"/root/TermOrganismGitFork/demo/helper_mod.py\", line 4, in read_log\n    return Path(\"logs/app.log\").read_text()\nFileNotFoundError: [Errno 2] No such file or directory: 'logs/app.log'\n",
        file_path="demo/cross_file_dep.py",
    )
    assert isinstance(result, dict)
    assert "ok" in result
    assert "file_path" in result
