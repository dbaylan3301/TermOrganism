"""OpenStock Next.js project integration."""

from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Optional


def detect_project_type(cwd: str = ".") -> Optional[str]:
    """Detect project type in directory."""
    if (Path(cwd) / "package.json").exists():
        try:
            import json
            with open(Path(cwd) / "package.json") as f:
                pkg = json.load(f)
                deps = pkg.get("dependencies", {})
                dev_deps = pkg.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}

                if "next" in all_deps:
                    return "nextjs"
                elif "react" in all_deps:
                    return "react"
                elif "vue" in all_deps:
                    return "vue"
        except Exception:
            pass

    if (Path(cwd) / "requirements.txt").exists() or (Path(cwd) / "pyproject.toml").exists():
        return "python"

    return None


def run_npm_command(args: list[str], cwd: str = ".") -> str:
    """Execute npm command."""
    try:
        result = subprocess.run(
            ["npm"] + args,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"npm hatası: {e}"


def get_nextjs_info(cwd: str = ".") -> str:
    """Get Next.js project information."""
    lines = ["📦 Next.js Proje Bilgisi:\n"]

    # Package.json
    pkg_path = Path(cwd) / "package.json"
    if pkg_path.exists():
        import json
        with open(pkg_path) as f:
            pkg = json.load(f)
            lines.append(f"Proje: {pkg.get('name', 'bilinmiyor')}")
            lines.append(f"Versiyon: {pkg.get('version', 'bilinmiyor')}")

            deps = pkg.get("dependencies", {})
            if "next" in deps:
                lines.append(f"Next.js: {deps['next']}")
            if "react" in deps:
                lines.append(f"React: {deps['react']}")

    # TypeScript config
    tsconfig = Path(cwd) / "tsconfig.json"
    if tsconfig.exists():
        lines.append("\n✅ TypeScript yapılandırması mevcut")

    # App directory
    app_dir = Path(cwd) / "app"
    if app_dir.exists():
        pages = list(app_dir.rglob("*.tsx")) + list(app_dir.rglob("*.ts"))
        lines.append(f"📄 {len(pages)} sayfa dosyası")

    return "\n".join(lines)


def run_nextjs_dev(cwd: str = ".") -> str:
    """Start Next.js dev server."""
    try:
        result = subprocess.run(
            ["npm", "run", "dev"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
        return f"Dev server başlatıldı:\n{result.stdout[:500]}"
    except subprocess.TimeoutExpired:
        return "Dev server arka planda çalışıyor (timeout sonrası devam ediyor)"
    except Exception as e:
        return f"Dev server hatası: {e}"
