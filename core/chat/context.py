from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ChatContext:
    cwd: str
    repo_root: str | None
    git_branch: str | None
    readme_path: str | None
    repo_type: str
    top_entries: list[str]


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def detect_context(cwd: str | None = None) -> ChatContext:
    base = Path(cwd or Path.cwd()).resolve()

    rc, repo_root, _ = _run(["git", "rev-parse", "--show-toplevel"], cwd=str(base))
    repo_root = repo_root if rc == 0 and repo_root else None

    rc, branch, _ = _run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=str(base))
    branch = branch if rc == 0 and branch else None

    probe_root = Path(repo_root) if repo_root else base

    readme_path = None
    for name in ["README.md", "readme.md", "README.rst", "README.txt"]:
        p = probe_root / name
        if p.exists():
            readme_path = str(p)
            break

    repo_type = "generic"
    if (probe_root / "pyproject.toml").exists() or (probe_root / "requirements.txt").exists():
        repo_type = "python_cli"
    elif (probe_root / "package.json").exists():
        repo_type = "node_app"

    top_entries = sorted([x.name for x in probe_root.iterdir()])[:20]

    return ChatContext(
        cwd=str(base),
        repo_root=repo_root,
        git_branch=branch,
        readme_path=readme_path,
        repo_type=repo_type,
        top_entries=top_entries,
    )


def summarize_repo(ctx: ChatContext) -> str:
    lines: list[str] = []
    lines.append(f"Çalışma dizini: {ctx.cwd}")
    if ctx.repo_root:
        lines.append(f"Repo kökü: {ctx.repo_root}")
    if ctx.git_branch:
        lines.append(f"Branch: {ctx.git_branch}")
    lines.append(f"Repo tipi: {ctx.repo_type}")

    if ctx.readme_path:
        p = Path(ctx.readme_path)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            cleaned = [ln.strip() for ln in text.splitlines() if ln.strip()]
            preview = cleaned[:8]
            if preview:
                lines.append("")
                lines.append("README özeti:")
                lines.extend(f"- {ln[:180]}" for ln in preview)
        except Exception:
            pass

    if ctx.top_entries:
        lines.append("")
        lines.append("Üst seviye içerik:")
        lines.extend(f"- {x}" for x in ctx.top_entries[:12])

    return "\n".join(lines)


def infer_run_command(ctx: ChatContext) -> tuple[str | None, str]:
    root = Path(ctx.repo_root or ctx.cwd)

    if ctx.repo_type == "python_cli":
        for name in ["main.py", "app.py", "run.py", "manage.py"]:
            p = root / name
            if p.exists():
                return f"python3 {name}", f"{name} giriş noktası bulundu"
        if (root / "pyproject.toml").exists():
            return "python3 -m pytest -q", "çalıştırma komutu net değil; test komutunu fallback seçtim"
        return None, "açık bir Python giriş noktası bulunamadı"

    if ctx.repo_type == "node_app":
        pkg = root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts") or {}
                if "dev" in scripts:
                    return "npm run dev", "package.json içinde dev script bulundu"
                if "start" in scripts:
                    return "npm start", "package.json içinde start script bulundu"
            except Exception:
                pass
        return None, "node projesi görünüyor ama script bulunamadı"

    return None, "çalıştırma komutu çıkarılamadı"
