from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import subprocess


def _run_git(args: list[str], cwd: str) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=12,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _signature_keywords(signature: str | None) -> set[str]:
    sig = (signature or "").lower()
    kws: set[str] = set()

    if any(x in sig for x in ["import", "module", "package"]):
        kws |= {"import", "module", "package", "path", "loader"}

    if any(x in sig for x in ["file", "directory", "path", "open", "read", "write"]):
        kws |= {"file", "directory", "path", "open", "read", "write"}

    if any(x in sig for x in ["syntax", "parse", "token", "ast"]):
        kws |= {"syntax", "parser", "token", "ast"}

    if any(x in sig for x in ["test", "pytest", "verify", "assert", "timeout"]):
        kws |= {"test", "pytest", "verify", "assert", "timeout", "suite"}

    kws |= {x for x in re.split(r"[^a-z0-9_]+", sig) if len(x) >= 4}
    return kws


def _tokenize_path(path_str: str) -> set[str]:
    return {x for x in re.split(r"[^a-zA-Z0-9_]+", path_str.lower()) if x}


def _read_recent_commits(repo_root: str, limit: int = 8) -> list[dict[str, Any]]:
    rc, out, _ = _run_git(
        [
            "log",
            f"-n{limit}",
            "--date=short",
            "--pretty=format:__COMMIT__%n%H%x1f%s%x1f%ad",
            "--name-only",
        ],
        cwd=repo_root,
    )
    if rc != 0 or not out:
        return []

    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in out.splitlines():
        line = raw_line.rstrip()
        if line == "__COMMIT__":
            if current:
                commits.append(current)
            current = {"hash": "", "subject": "", "date": "", "files": []}
            continue

        if current is None:
            continue

        if not current["hash"] and "\x1f" in line:
            parts = line.split("\x1f")
            current["hash"] = parts[0]
            current["subject"] = parts[1] if len(parts) > 1 else ""
            current["date"] = parts[2] if len(parts) > 2 else ""
            continue

        if line.strip():
            current["files"].append(line.strip())

    if current:
        commits.append(current)

    return commits


def build_semantic_scent(
    *,
    repo_root: str,
    target_path: str | None = None,
    signature: str | None = None,
    commit_limit: int = 8,
) -> dict[str, Any] | None:
    root = Path(repo_root).resolve()
    if not root.exists():
        return None

    target_rel: str | None = None
    if target_path:
        try:
            target_rel = str(Path(target_path).resolve().relative_to(root))
        except Exception:
            target_rel = None

    commits = _read_recent_commits(str(root), limit=commit_limit)
    if not commits:
        return {
            "signature": signature or "-",
            "why_now": "git geçmişi okunamadı; yalnızca sınırlı bağlam var",
            "suspect_files": [],
            "change_correlation": 0.0,
            "scent_score": 0.0,
            "recent_commit_subjects": [],
        }

    kw = _signature_keywords(signature)
    target_tokens = _tokenize_path(target_rel or "")

    file_scores: dict[str, float] = {}
    subject_hits = 0
    target_hits = 0

    for idx, commit in enumerate(commits):
        recency = max(0.25, 1.0 - (idx * 0.08))
        subject = str(commit.get("subject", ""))
        subject_l = subject.lower()

        if kw and any(k in subject_l for k in kw):
            subject_hits += 1

        for file in commit.get("files", []):
            score = 0.0
            fpath = str(file)
            ftokens = _tokenize_path(fpath)

            if target_rel:
                if fpath == target_rel:
                    score += 0.55
                    target_hits += 1
                else:
                    try:
                        if Path(fpath).parent == Path(target_rel).parent:
                            score += 0.32
                            target_hits += 1
                    except Exception:
                        pass
                    if Path(fpath).suffix and Path(fpath).suffix == Path(target_rel).suffix:
                        score += 0.10
                    if target_tokens & ftokens:
                        score += min(0.22, 0.04 * len(target_tokens & ftokens))

            if kw:
                overlap = kw & ftokens
                if overlap:
                    score += min(0.28, 0.05 * len(overlap))
                if any(k in subject_l for k in kw):
                    score += 0.10

            if score > 0:
                file_scores[fpath] = file_scores.get(fpath, 0.0) + (score * recency)

    suspects = sorted(file_scores.items(), key=lambda kv: kv[1], reverse=True)
    suspect_files = [name for name, _ in suspects[:5]]

    top_score = suspects[0][1] if suspects else 0.0
    norm_top = min(1.0, top_score)
    message_factor = min(1.0, subject_hits / max(1, len(commits)))
    target_factor = min(1.0, target_hits / max(1, len(commits)))

    change_correlation = round(min(1.0, (norm_top * 0.55) + (message_factor * 0.25) + (target_factor * 0.20)), 4)
    scent_score = round(min(1.0, (norm_top * 0.60) + (message_factor * 0.20) + (target_factor * 0.20)), 4)

    why_parts: list[str] = []

    if target_rel and suspect_files:
        if suspect_files[0] == target_rel:
            why_parts.append("hedef dosya son değişim alanına çok yakın görünüyor")
        else:
            why_parts.append("hedefe yakın dosyalarda yakın zamanda değişim var")

    if subject_hits:
        why_parts.append("commit mesajları hata desenine semantik olarak yakın")

    if not why_parts and suspects:
        why_parts.append("aktif değişim bölgesi ile mevcut arıza arasında korelasyon var")

    if not why_parts:
        why_parts.append("sınırlı bağlamda belirgin bir değişim kokusu alınmadı")

    return {
        "signature": signature or "-",
        "why_now": "; ".join(why_parts),
        "suspect_files": suspect_files,
        "change_correlation": change_correlation,
        "scent_score": scent_score,
        "recent_commit_subjects": [str(c.get("subject", "")) for c in commits[:4]],
    }
