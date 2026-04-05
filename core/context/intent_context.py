from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
import re
import subprocess


DOMAIN_MAP: dict[str, set[str]] = {
    "authentication": {"auth", "login", "token", "session", "oauth", "jwt", "credential", "user"},
    "testing": {"test", "pytest", "verify", "assert", "mock", "fixture"},
    "daemon_runtime": {"daemon", "runtime", "server", "socket", "worker", "pool"},
    "ui_output": {"ui", "pretty", "panel", "output", "render", "chat", "narrator"},
    "memory_routing": {"memory", "synaptic", "planner", "route", "routing", "repair"},
}


def _run_git(args: list[str], cwd: str) -> tuple[int, str, str]:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _tokens(text: str) -> set[str]:
    return {x for x in re.split(r"[^a-zA-Z0-9_]+", text.lower()) if x}


def _modified_files(repo_root: str) -> list[str]:
    rc, out, _ = _run_git(["status", "--short"], repo_root)
    if rc != 0 or not out:
        return []
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip())
    return files[:20]


def _recent_subjects(repo_root: str, limit: int = 5) -> list[str]:
    rc, out, _ = _run_git(["log", f"-n{limit}", "--pretty=format:%s"], repo_root)
    if rc != 0 or not out:
        return []
    return [x.strip() for x in out.splitlines() if x.strip()][:limit]


def infer_intent_context(ctx) -> dict[str, Any]:
    repo_root = str(ctx.repo_root or ctx.cwd)
    branch = str(ctx.git_branch or "")
    modified = _modified_files(repo_root)
    subjects = _recent_subjects(repo_root, limit=5)

    scores: dict[str, float] = defaultdict(float)

    evidence_chunks = [branch, *modified[:10], *subjects[:5]]
    for chunk in evidence_chunks:
        toks = _tokens(chunk)
        for label, vocab in DOMAIN_MAP.items():
            overlap = toks & vocab
            if overlap:
                scores[label] += 1.0 + (0.2 * len(overlap))

    if scores:
        best_label = max(scores, key=scores.get)
        total = sum(scores.values()) or 1.0
        confidence = round(min(0.99, scores[best_label] / total + 0.35), 4)
    else:
        best_label = "general_runtime"
        confidence = 0.42

    preload_routes_map = {
        "authentication": ["import_guard", "safe_preview", "narrow_auth_tests"],
        "testing": ["narrow_test_first", "verify_before_broad"],
        "daemon_runtime": ["socket_guard", "daemon_verify", "process_check"],
        "ui_output": ["render_verify", "pretty_output_check", "chat_narrator_verify"],
        "memory_routing": ["synaptic_prior_check", "planner_verify", "safe_preview"],
        "general_runtime": ["safe_preview", "verify_first"],
    }

    return {
        "focus": best_label,
        "confidence": confidence,
        "branch": branch or "-",
        "modified_files": modified[:6],
        "recent_subjects": subjects[:4],
        "preload_routes": preload_routes_map.get(best_label, ["safe_preview", "verify_first"]),
    }
