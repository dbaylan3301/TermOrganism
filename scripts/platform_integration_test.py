#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOCKET = Path("/tmp/termorganism.sock")
STATE_FILE = ROOT / ".termorganism/plugins_state.json"


def wait_for_socket(timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if SOCKET.exists():
            return True
        time.sleep(0.05)
    return False


def start_daemon():
    try:
        SOCKET.unlink(missing_ok=True)
    except Exception:
        pass

    proc = subprocess.Popen(
        [sys.executable, "-m", "core.daemon.server"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if not wait_for_socket():
        proc.terminate()
        raise RuntimeError("daemon socket did not appear")
    return proc


def run_json(cmd: str) -> dict:
    res = subprocess.run(
        cmd,
        cwd=str(ROOT),
        shell=True,
        capture_output=True,
        text=True,
    )
    stdout = res.stdout.strip()
    if not stdout:
        raise RuntimeError(f"empty stdout for: {cmd}")
    try:
        return json.loads(stdout)
    except Exception as e:
        raise RuntimeError(f"json parse failed for {cmd}: {e}\nSTDOUT={stdout[:500]}\nSTDERR={res.stderr[:500]}")


def reset_plugin_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"enabled": [], "disabled": []}, indent=2), encoding="utf-8")


def prepare_fixtures():
    Path("/tmp/hook_block_case.py").write_text(
        'import definitely_missing_package_12345\n',
        encoding="utf-8",
    )


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def test_plugins_list():
    data = run_json("./termorganism plugins list")
    assert_true(data.get("success") is True, f"plugins list failed: {data}")
    names = [p.get("name") for p in data.get("plugins", [])]
    assert_true("python-hotfix" in names, f"python-hotfix missing: {data}")
    return {"plugins": names}


def test_plugins_disable_enable():
    data1 = run_json("./termorganism plugins disable python-hotfix")
    assert_true(data1.get("success") is True, f"disable failed: {data1}")
    state1 = data1.get("state", {})
    assert_true("python-hotfix" in state1.get("disabled", []), f"disable state wrong: {data1}")

    data2 = run_json("./termorganism plugins enable python-hotfix")
    assert_true(data2.get("success") is True, f"enable failed: {data2}")
    state2 = data2.get("state", {})
    assert_true("python-hotfix" in state2.get("enabled", []), f"enable state wrong: {data2}")
    return {"disable": state1, "enable": state2}


def test_hook_block():
    data = run_json(
        "TERMORGANISM_FAST_V2=1 TERMORGANISM_USE_DAEMON=1 ./termorganism.sh repair /tmp/hook_block_case.py"
    )
    assert_true(data.get("mode") == "hook_block", f"unexpected hook_block mode: {data}")
    assert_true(data.get("error") == "hook_blocked", f"unexpected hook_block error: {data}")
    return {"hook_block": data.get("hook")}


def current_branch() -> str:
    res = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(ROOT), text=True).strip()
    return res


def test_auto_commit_and_undo():
    base_branch = current_branch()
    cmd = (
        "TERMORGANISM_FAST_V2=1 TERMORGANISM_USE_DAEMON=1 "
        "./termorganism.sh repair demo/broken_runtime.py "
        "--git-undo --git-branch --git-commit "
        "--git-branch-name=termorganism/platform-test "
        '--git-commit-message="termorganism: platform integration auto commit"'
    )
    data = run_json(cmd)
    gitops = data.get("gitops", {})
    assert_true(data.get("success") is True, f"auto commit repair failed: {data}")
    assert_true(gitops.get("enabled") is True, f"gitops disabled: {data}")
    assert_true(bool(gitops.get("undo_ref")), f"undo_ref missing: {data}")
    assert_true(bool(gitops.get("branch")), f"branch missing: {data}")
    assert_true(bool(gitops.get("commit_sha")), f"commit_sha missing: {data}")

    undo_ref = gitops["undo_ref"]
    undo_data = run_json(f"TERMORGANISM_USE_DAEMON=1 ./termorganism.sh undo demo/broken_runtime.py --undo-ref={undo_ref}")
    assert_true(undo_data.get("success") is True, f"undo failed: {undo_data}")

    # return to base branch for cleanliness
    subprocess.run(["git", "checkout", base_branch], cwd=str(ROOT), check=True)
    return {
        "gitops": gitops,
        "undo": undo_data,
    }


def main() -> int:
    reset_plugin_state()
    prepare_fixtures()

    tests = []
    daemon = start_daemon()
    try:
        tests.append(("plugins_list", test_plugins_list()))
        tests.append(("plugins_disable_enable", test_plugins_disable_enable()))

        # daemon reload required after plugin state change
        daemon.terminate()
        try:
            daemon.wait(timeout=3)
        except Exception:
            daemon.kill()

        daemon = start_daemon()

        tests.append(("hook_block", test_hook_block()))
        tests.append(("auto_commit_and_undo", test_auto_commit_and_undo()))
    finally:
        daemon.terminate()
        try:
            daemon.wait(timeout=3)
        except Exception:
            daemon.kill()

        # restore clean plugin state
        reset_plugin_state()

    print(json.dumps({
        "success": True,
        "tests": tests,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
