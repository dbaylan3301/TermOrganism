from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any


ALLOWED_BASE_COMMANDS = {
    "command",
    "which",
    "echo",
    "mkdir",
    "touch",
    "chmod",
}


def _is_safe_tokens(tokens: list[str]) -> tuple[bool, str]:
    if not tokens:
        return False, "empty command"

    base = tokens[0]

    if base not in ALLOWED_BASE_COMMANDS:
        return False, f"base command not allowed: {base}"

    if base == "command":
        if len(tokens) != 3 or tokens[1] != "-v":
            return False, "only 'command -v <name>' allowed"
        return True, "ok"

    if base == "which":
        if len(tokens) != 2:
            return False, "only 'which <name>' allowed"
        return True, "ok"

    if base == "echo":
        if tokens != ["echo", "$PATH"]:
            return False, "only 'echo $PATH' allowed"
        return True, "ok"

    if base == "mkdir":
        if len(tokens) < 3 or tokens[1] != "-p":
            return False, "only 'mkdir -p <path>' allowed"
        return True, "ok"

    if base == "touch":
        if len(tokens) != 2:
            return False, "only 'touch <path>' allowed"
        return True, "ok"

    if base == "chmod":
        if len(tokens) != 3 or tokens[1] != "+x":
            return False, "only 'chmod +x <path>' allowed"
        return True, "ok"

    return False, "unhandled command"


def _normalize_commands(command_text: str | None) -> list[str]:
    if not command_text or not isinstance(command_text, str):
        return []
    parts = [p.strip() for p in command_text.split("&&")]
    return [p for p in parts if p]


def execute_safe_suggestions(
    command_text: str | None,
    *,
    dry_run: bool = False,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    commands = _normalize_commands(command_text)
    results: list[dict[str, Any]] = []

    if not commands:
        return {
            "executed": False,
            "dry_run": dry_run,
            "results": [],
            "reason": "no commands to execute",
        }

    workdir = str(cwd) if cwd else None

    for cmd in commands:
        tokens = shlex.split(cmd)
        ok, reason = _is_safe_tokens(tokens)

        if not ok:
            results.append({
                "command": cmd,
                "allowed": False,
                "executed": False,
                "reason": reason,
            })
            continue

        if dry_run:
            results.append({
                "command": cmd,
                "allowed": True,
                "executed": False,
                "reason": "dry-run",
            })
            continue

        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        results.append({
            "command": cmd,
            "allowed": True,
            "executed": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })

    executed_any = any(r.get("executed", False) for r in results)
    all_allowed = all(r.get("allowed", False) for r in results) if results else False

    return {
        "executed": executed_any,
        "dry_run": dry_run,
        "all_allowed": all_allowed,
        "results": results,
    }
