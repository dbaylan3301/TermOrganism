"""Dependency analysis for projects."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional


def analyze_python_deps(project_dir: str = ".") -> Dict:
    """Analyze Python dependencies."""
    result = {
        "requirements": [],
        "pyproject": None,
        "outdated": [],
        "security_issues": [],
    }
    
    # Check requirements.txt
    req_file = Path(project_dir) / "requirements.txt"
    if req_file.exists():
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    result["requirements"].append(line)
    
    # Check pyproject.toml
    pyproject = Path(project_dir) / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                deps = data.get("project", {}).get("dependencies", [])
                result["pyproject"] = deps
        except Exception:
            pass
    
    return result


def analyze_node_deps(project_dir: str = ".") -> Dict:
    """Analyze Node.js dependencies."""
    result = {
        "dependencies": {},
        "devDependencies": {},
        "scripts": {},
        "engines": {},
    }
    
    pkg_file = Path(project_dir) / "package.json"
    if pkg_file.exists():
        with open(pkg_file) as f:
            pkg = json.load(f)
            result["dependencies"] = pkg.get("dependencies", {})
            result["devDependencies"] = pkg.get("devDependencies", {})
            result["scripts"] = pkg.get("scripts", {})
            result["engines"] = pkg.get("engines", {})
    
    return result


def format_dependency_report(python_deps: Dict, node_deps: Dict) -> str:
    """Format dependency report."""
    lines = ["📦 Bağlantı Raporu:\n"]
    
    # Python
    if python_deps["requirements"]:
        lines.append(f"🐍 Python ({len(python_deps['requirements'])} paket):")
        for dep in python_deps["requirements"][:10]:
            lines.append(f"  • {dep}")
    
    # Node.js
    if node_deps["dependencies"]:
        lines.append(f"\n📦 Node.js ({len(node_deps['dependencies'])} prod, {len(node_deps['devDependencies'])} dev):")
        for pkg, version in list(node_deps["dependencies"].items())[:10]:
            lines.append(f"  • {pkg}: {version}")
        
        if node_deps["scripts"]:
            lines.append(f"\n📋 Scripts:")
            for script, cmd in list(node_deps["scripts"].items())[:5]:
                lines.append(f"  • {script}: {cmd}")
    
    return "\n".join(lines)