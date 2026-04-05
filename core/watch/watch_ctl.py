from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path


def _state_dir() -> Path:
    base = Path.home() / ".termorganism" / "watch"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _pid_file() -> Path:
    return _state_dir() / "watch.pid"


def _log_file() -> Path:
    return _state_dir() / "watch.log"


def _cmd_file() -> Path:
    return _state_dir() / "watch.cmd"


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid() -> int | None:
    p = _pid_file()
    if not p.exists():
        return None
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def status_text() -> str:
    pid = _read_pid()
    if not pid:
        return f"STOPPED\npid_file={_pid_file()}\nlog_file={_log_file()}"
    if not _is_running(pid):
        return f"STALE\npid={pid}\npid_file={_pid_file()}\nlog_file={_log_file()}"
    cmd = _cmd_file().read_text(encoding="utf-8").strip() if _cmd_file().exists() else "-"
    return f"RUNNING\npid={pid}\ncmd={cmd}\npid_file={_pid_file()}\nlog_file={_log_file()}"


def start_watch(args: argparse.Namespace) -> int:
    pid = _read_pid()
    if pid and _is_running(pid):
        print(status_text())
        return 0

    log_path = _log_file()
    cmd = [
        sys.executable,
        "-m",
        "core.watch.watch_cli",
    ]
    if args.modified:
        cmd.append("--modified")
    if args.loop:
        cmd.append("--loop")
    cmd.extend(["--interval", str(args.interval)])
    cmd.extend(args.paths)

    with log_path.open("ab") as logf:
        proc = subprocess.Popen(
            cmd,
            cwd="/root/TermOrganismGitFork",
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    _pid_file().write_text(str(proc.pid), encoding="utf-8")
    _cmd_file().write_text(" ".join(cmd), encoding="utf-8")
    print(f"STARTED\npid={proc.pid}\nlog_file={log_path}")
    return 0


def stop_watch() -> int:
    pid = _read_pid()
    if not pid:
        print("STOPPED\nreason=no_pid")
        return 0

    if not _is_running(pid):
        with contextlib_suppress():
            _pid_file().unlink()
        print(f"STALE_CLEANED\npid={pid}")
        return 0

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        print(f"STOP_FAILED\npid={pid}\nerror={e}")
        return 1

    with contextlib_suppress():
        _pid_file().unlink()

    print(f"STOPPED\npid={pid}")
    return 0


class contextlib_suppress:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return True


def main() -> int:
    parser = argparse.ArgumentParser(prog="termorganism-watch-ctl")
    sub = parser.add_subparsers(dest="action", required=True)

    p_start = sub.add_parser("start")
    p_start.add_argument("paths", nargs="*")
    p_start.add_argument("--modified", action="store_true")
    p_start.add_argument("--loop", action="store_true", default=True)
    p_start.add_argument("--interval", type=float, default=2.0)

    sub.add_parser("stop")
    sub.add_parser("status")

    args = parser.parse_args()

    if args.action == "start":
        return start_watch(args)
    if args.action == "stop":
        return stop_watch()
    if args.action == "status":
        print(status_text())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
