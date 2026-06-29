# TermOrganism Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend TermOrganism REPL with advanced features, OpenStock integration, auto-repair, and enhanced analysis capabilities.

**Architecture:** Modular extension of existing REPL structure with new command handlers, project-specific integrations, and automated repair workflows.

**Tech Stack:** Python 3.11+, Rich TUI framework, MiMo AI integration, subprocess for tool execution.

---

## Task 1: Enhanced REPL Commands

**Covers:** REPL expansion requirements

**Files:**
- Modify: `core/ui/repl.py:138-282`
- Create: `core/commands/enhanced.py`

- [ ] **Step 1: Create enhanced commands module**

```python
# core/commands/enhanced.py
"""Enhanced REPL commands for TermOrganism."""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_git_command(args: list[str], cwd: str = ".") -> str:
    """Execute git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git hatası: {e}"


def get_repo_summary(cwd: str = ".") -> str:
    """Get repository summary."""
    lines = []
    
    # Get project name
    readme = Path(cwd) / "README.md"
    if readme.exists():
        with open(readme, "r", encoding="utf-8") as f:
            first_lines = f.readlines()[:10]
            lines.append("".join(first_lines[:3]).strip())
    
    # Get file count
    py_files = list(Path(cwd).rglob("*.py"))
    ts_files = list(Path(cwd).rglob("*.ts"))
    js_files = list(Path(cwd).rglob("*.js"))
    
    lines.append(f"\n📊 İstatistikler:")
    lines.append(f"  Python: {len(py_files)} dosya")
    lines.append(f"  TypeScript: {len(ts_files)} dosya")
    lines.append(f"  JavaScript: {len(js_files)} dosya")
    
    return "\n".join(lines)


def get_repo_status(cwd: str = ".") -> str:
    """Get repository status."""
    lines = ["📊 Repo Durumu:\n"]
    
    # Branch info
    branch = run_git_command(["branch", "--show-current"], cwd)
    lines.append(f"Branch: {branch.strip()}")
    
    # Status
    status = run_git_command(["status", "--short"], cwd)
    if status.strip():
        lines.append(f"\nDeğişiklikler:\n{status}")
    else:
        lines.append("\n✅ Working tree temiz")
    
    # Recent commits
    commits = run_git_command(["log", "--oneline", "-5"], cwd)
    if commits.strip():
        lines.append(f"\nSon 5 commit:\n{commits}")
    
    return "\n".join(lines)
```

- [ ] **Step 2: Update REPL with enhanced commands**

```python
# Add to core/ui/repl.py after imports
from core.commands.enhanced import get_repo_summary, get_repo_status

# Update intent detection in repl_entry function
# Add after line 219 (watch intent):
elif any(w in msg_lower for w in ["repo özeti", "proje ne", "bu ne", "proje hakkında"]):
    intent = "repo_summary"
elif any(w in msg_lower for w in ["repo durumu", "git status", "değişiklikler"]):
    intent = "repo_status"

# Add handlers after watch handler (line 237):
elif intent == "repo_summary":
    _render_response(get_repo_summary())
    history.append({"role": "assistant", "content": "Repo özeti gösterildi."})
    continue
elif intent == "repo_status":
    _render_response(get_repo_status())
    history.append({"role": "assistant", "content": "Repo durumu gösterildi."})
    continue
```

- [ ] **Step 3: Test enhanced commands**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
echo -e "repo özeti\nrepo durumu\nexit" | timeout 15 python -m core.ui.repl
```

- [ ] **Step 4: Commit changes**

```bash
git add core/commands/enhanced.py core/ui/repl.py
git commit -m "feat: add enhanced REPL commands (repo summary, status)"
```

---

## Task 2: OpenStock Integration

**Covers:** OpenStock Next.js project integration

**Files:**
- Create: `core/integrations/openstock.py`
- Modify: `core/ui/repl.py:204-224`

- [ ] **Step 1: Create OpenStock integration module**

```python
# core/integrations/openstock.py
"""OpenStock Next.js project integration."""

from __future__ import annotations
import subprocess
import sys
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
```

- [ ] **Step 2: Add OpenStock detection to REPL**

```python
# Add to core/ui/repl.py imports
from core.integrations.openstock import detect_project_type, get_nextjs_info

# Add new intent detection after line 219:
elif any(w in msg_lower for w in ["nextjs", "next.js", "react proje", "ts proje"]):
    intent = "project_info"
elif any(w in msg_lower for w in ["dev başlat", "sunucu başlat", "npm dev"]):
    intent = "run_dev"

# Add handlers after repo_status handler:
elif intent == "project_info":
    project_type = detect_project_type()
    if project_type == "nextjs":
        _render_response(get_nextjs_info())
    else:
        _render_response(f"Proje tipi: {project_type or 'bilinmiyor'}")
    history.append({"role": "assistant", "content": "Proje bilgisi gösterildi."})
    continue
elif intent == "run_dev":
    project_type = detect_project_type()
    if project_type == "nextjs":
        _render_response(run_nextjs_dev())
    else:
        _render_response("Bu komut sadece Next.js projeleri için çalışır.")
    history.append({"role": "assistant", "content": "Dev server komutu çalıştırıldı."})
    continue
```

- [ ] **Step 3: Test OpenStock integration**

```bash
cd /home/craftzzdog/Desktop/OpenStock
source /home/craftzzdog/TermOrganism/venv/bin/activate
echo -e "nextjs bilgi\nexit" | timeout 15 python -m core.ui.repl
```

- [ ] **Step 4: Commit changes**

```bash
git add core/integrations/openstock.py core/ui/repl.py
git commit -m "feat: add OpenStock/Next.js integration"
```

---

## Task 3: Auto-Repair System

**Covers:** Automatic error detection and repair

**Files:**
- Create: `core/repair/auto_fix.py`
- Modify: `core/ui/repl.py:204-224`

- [ ] **Step 1: Create auto-repair module**

```python
# core/repair/auto_fix.py
"""Automatic error detection and repair system."""

from __future__ import annotations
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, List


def run_linter(filepath: str) -> List[Dict]:
    """Run linter on file and return issues."""
    issues = []
    
    # Python files
    if filepath.endswith(".py"):
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", filepath],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                issues.append({
                    "type": "syntax",
                    "message": result.stderr,
                    "file": filepath,
                })
        except Exception as e:
            issues.append({"type": "error", "message": str(e), "file": filepath})
    
    # JavaScript/TypeScript files
    elif filepath.endswith((".js", ".ts", ".tsx", ".jsx")):
        try:
            result = subprocess.run(
                ["npx", "eslint", filepath, "--format=json"],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                import json
                eslint_issues = json.loads(result.stdout)
                for issue in eslint_issues:
                    for msg in issue.get("messages", []):
                        issues.append({
                            "type": "lint",
                            "message": msg.get("message", ""),
                            "line": msg.get("line", 0),
                            "file": filepath,
                        })
        except Exception:
            pass
    
    return issues


def analyze_code_quality(filepath: str) -> Dict:
    """Analyze code quality metrics."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            
        metrics = {
            "file": filepath,
            "lines": len(lines),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "comment_lines": sum(1 for l in lines if l.strip().startswith(("#", "//", "/*"))),
            "functions": len(re.findall(r"(?:def|function|const\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|\function))", content)),
            "classes": len(re.findall(r"class\s+\w+", content)),
            "imports": len(re.findall(r"(?:import|from|require)", content)),
        }
        
        # Calculate complexity indicators
        metrics["complexity_indicators"] = []
        if metrics["lines"] > 500:
            metrics["complexity_indicators"].append("Uzun dosya (500+ satır)")
        if metrics["functions"] > 20:
            metrics["complexity_indicators"].append("Çok fazla fonksiyon (20+)")
        if content.count("TODO") > 3:
            metrics["complexity_indicators"].append("Çok fazla TODO notu")
            
        return metrics
    except Exception as e:
        return {"error": str(e), "file": filepath}


def scan_project(project_dir: str = ".") -> Dict:
    """Scan project for issues."""
    results = {
        "total_files": 0,
        "files_with_issues": 0,
        "issues": [],
        "quality_metrics": [],
    }
    
    project_path = Path(project_dir)
    
    # Scan Python files
    for py_file in project_path.rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        results["total_files"] += 1
        issues = run_linter(str(py_file))
        if issues:
            results["files_with_issues"] += 1
            results["issues"].extend(issues)
        
        metrics = analyze_code_quality(str(py_file))
        if "error" not in metrics:
            results["quality_metrics"].append(metrics)
    
    # Scan JS/TS files
    for js_file in list(project_path.rglob("*.js")) + list(project_path.rglob("*.ts")):
        if "node_modules" in str(js_file):
            continue
            
        results["total_files"] += 1
        issues = run_linter(str(js_file))
        if issues:
            results["files_with_issues"] += 1
            results["issues"].extend(issues)
    
    return results


def format_scan_results(results: Dict) -> str:
    """Format scan results for display."""
    lines = ["🔍 Proje Tarama Sonuçları:\n"]
    lines.append(f"📊 Toplam dosya: {results['total_files']}")
    lines.append(f"⚠️  Sorunlu dosya: {results['files_with_issues']}")
    lines.append(f"🔧 Toplam sorun: {len(results['issues'])}")
    
    if results["issues"]:
        lines.append("\n🚨 Tespit Edilen Sorunlar:")
        for i, issue in enumerate(results["issues"][:10], 1):
            lines.append(f"  {i}. [{issue['type']}] {issue['file']}")
            lines.append(f"     {issue['message'][:100]}")
    
    if results["quality_metrics"]:
        lines.append("\n📈 Kod Kalitesi:")
        for metric in results["quality_metrics"][:5]:
            if metric.get("complexity_indicators"):
                lines.append(f"  {Path(metric['file']).name}: {', '.join(metric['complexity_indicators'])}")
    
    return "\n".join(lines)
```

- [ ] **Step 2: Add auto-repair commands to REPL**

```python
# Add to core/ui/repl.py imports
from core.repair.auto_fix import scan_project, format_scan_results

# Add new intent detection after line 219:
elif any(w in msg_lower for w in ["tara", "scan", "hata bul", "sorun bul"]):
    intent = "scan"
elif any(w in msg_lower for w in ["onar", "fix", "tamir", "düzelt"]):
    intent = "repair"

# Add handlers after run_dev handler:
elif intent == "scan":
    results = scan_project(".")
    _render_response(format_scan_results(results))
    history.append({"role": "assistant", "content": "Proje taraması tamamlandı."})
    continue
elif intent == "repair":
    results = scan_project(".")
    if results["issues"]:
        _render_response(f"🔍 {len(results['issues'])} sorun bulundu.\n\nOtomatik onarım henüz geliştirme aşamasında.\nManuel düzeltme için sorunlu dosyaları belirtebilirsiniz.")
    else:
        _render_response("✅ Herhangi bir sorun bulunamadı!")
    history.append({"role": "assistant", "content": "Onarım kontrolü tamamlandı."})
    continue
```

- [ ] **Step 3: Test auto-repair system**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
echo -e "tara\nexit" | timeout 20 python -m core.ui.repl
```

- [ ] **Step 4: Commit changes**

```bash
git add core/repair/auto_fix.py core/ui/repl.py
git commit -m "feat: add auto-repair and code quality analysis"
```

---

## Task 4: Enhanced Analysis Features

**Covers:** Advanced code analysis and security scanning

**Files:**
- Create: `core/analysis/security.py`
- Create: `core/analysis/dependencies.py`
- Modify: `core/ui/repl.py:204-224`

- [ ] **Step 1: Create security analysis module**

```python
# core/analysis/security.py
"""Security analysis for code files."""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict


SECURITY_PATTERNS = {
    "hardcoded_secret": [
        (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"(?:api_key|apikey|api-key)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (r"(?:secret|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret/token"),
        (r"['\"][A-Za-z0-9]{32,}['\"]", "Potential secret string"),
    ],
    "sql_injection": [
        (r"(?:execute|cursor\.execute)\s*\(\s*f['\"]", "F-string SQL injection risk"),
        (r"(?:execute|cursor\.execute)\s*\(\s*['\"].*%s", "String formatting SQL injection risk"),
        (r"(?:execute|cursor\.execute)\s*\(\s*['\"].*\+", "String concatenation SQL injection risk"),
    ],
    "xss_risk": [
        (r"innerHTML\s*=", "innerHTML XSS risk"),
        (r"dangerouslySetInnerHTML", "React dangerouslySetInnerHTML"),
        (r"document\.write\(", "document.write XSS risk"),
    ],
    "insecure_random": [
        (r"random\.(?:random|randint|choice)", "Insecure random for security"),
        (r"Math\.random\(\)", "Math.random() for security"),
    ],
    "eval_usage": [
        (r"eval\(", "eval() usage"),
        (r"exec\(", "exec() usage"),
        (r"subprocess\.call\([^)]+shell\s*=\s*True", "Shell=True in subprocess"),
    ],
}


def scan_file_security(filepath: str) -> List[Dict]:
    """Scan file for security issues."""
    issues = []
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
            
        for category, patterns in SECURITY_PATTERNS.items():
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({
                            "category": category,
                            "description": description,
                            "file": filepath,
                            "line": line_num,
                            "code": line.strip()[:100],
                        })
    except Exception as e:
        issues.append({
            "category": "error",
            "description": f"Scan error: {e}",
            "file": filepath,
        })
    
    return issues


def format_security_results(issues: List[Dict]) -> str:
    """Format security scan results."""
    if not issues:
        return "🔒 Güvenlik taraması: Sorun bulunamadı!"
    
    lines = ["🔒 Güvenlik Tarama Sonuçları:\n"]
    
    # Group by category
    by_category = {}
    for issue in issues:
        cat = issue["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(issue)
    
    for category, cat_issues in by_category.items():
        emoji = {
            "hardcoded_secret": "🔑",
            "sql_injection": "💉",
            "xss_risk": "🌐",
            "insecure_random": "🎲",
            "eval_usage": "⚠️",
            "error": "❌",
        }.get(category, "•")
        
        lines.append(f"\n{emoji} {category.upper()} ({len(cat_issues)} sorun):")
        for issue in cat_issues[:5]:
            lines.append(f"  • {issue['file']}:{issue['line']}")
            lines.append(f"    {issue['description']}")
            if issue.get("code"):
                lines.append(f"    Kod: {issue['code'][:60]}...")
    
    return "\n".join(lines)
```

- [ ] **Step 2: Create dependency analysis module**

```python
# core/analysis/dependencies.py
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
```

- [ ] **Step 3: Add analysis commands to REPL**

```python
# Add to core/ui/repl.py imports
from core.analysis.security import scan_file_security, format_security_results
from core.analysis.dependencies import analyze_python_deps, analyze_node_deps, format_dependency_report

# Add new intent detection after line 219:
elif any(w in msg_lower for w in ["güvenlik", "security", "siber", "güvenlik tara"]):
    intent = "security"
elif any(w in msg_lower for w in ["bağlantılar", "dependencies", "paketler", "bağlantı raporu"]):
    intent = "dependencies"

# Add handlers after repair handler:
elif intent == "security":
    # Scan current directory
    all_issues = []
    for py_file in Path(".").rglob("*.py"):
        if "venv" not in str(py_file):
            all_issues.extend(scan_file_security(str(py_file)))
    _render_response(format_security_results(all_issues))
    history.append({"role": "assistant", "content": "Güvenlik taraması tamamlandı."})
    continue
elif intent == "dependencies":
    python_deps = analyze_python_deps(".")
    node_deps = analyze_node_deps(".")
    _render_response(format_dependency_report(python_deps, node_deps))
    history.append({"role": "assistant", "content": "Bağlantı raporu gösterildi."})
    continue
```

- [ ] **Step 4: Test enhanced analysis**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
echo -e "güvenlik tara\nbağlantılar\nexit" | timeout 25 python -m core.ui.repl
```

- [ ] **Step 5: Commit changes**

```bash
git add core/analysis/security.py core/analysis/dependencies.py core/ui/repl.py
git commit -m "feat: add security scanning and dependency analysis"
```

---

## Task 5: Integration Testing

**Covers:** End-to-end testing of all new features

**Files:**
- Create: `tests/test_enhanced_repl.py`

- [ ] **Step 1: Create integration tests**

```python
# tests/test_enhanced_repl.py
"""Integration tests for enhanced REPL features."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_repo_summary():
    """Test repo summary command."""
    from core.commands.enhanced import get_repo_summary
    result = get_repo_summary()
    assert isinstance(result, str)
    assert "İstatistikler" in result


def test_repo_status():
    """Test repo status command."""
    from core.commands.enhanced import get_repo_status
    result = get_repo_status()
    assert isinstance(result, str)
    assert "Branch" in result


def test_project_detection():
    """Test project type detection."""
    from core.integrations.openstock import detect_project_type
    # Test in TermOrganism directory (Python project)
    result = detect_project_type(str(Path(__file__).parent.parent))
    assert result == "python"


def test_code_quality_analysis():
    """Test code quality analysis."""
    from core.repair.auto_fix import analyze_code_quality
    result = analyze_code_quality(str(Path(__file__).parent.parent / "core" / "ui" / "repl.py"))
    assert "lines" in result
    assert "functions" in result


def test_security_scan():
    """Test security scanning."""
    from core.analysis.security import scan_file_security
    issues = scan_file_security(str(Path(__file__).parent.parent / "core" / "ui" / "repl.py"))
    assert isinstance(issues, list)


def test_dependency_analysis():
    """Test dependency analysis."""
    from core.analysis.dependencies import analyze_python_deps
    result = analyze_python_deps(str(Path(__file__).parent.parent))
    assert "requirements" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: Run integration tests**

```bash
cd /home/craftzzdog/TermOrganism
source venv/bin/activate
python -m pytest tests/test_enhanced_repl.py -v
```

- [ ] **Step 3: Commit test file**

```bash
git add tests/test_enhanced_repl.py
git commit -m "test: add integration tests for enhanced REPL features"
```

---

## Execution Handoff

After completing all tasks, verify the implementation:

1. Run the REPL with test commands
2. Test each new feature individually
3. Ensure no regressions in existing functionality
4. Update README.md with new commands if needed

**Next Steps:**
- Deploy to OpenStock project for real-world testing
- Add more advanced repair algorithms
- Implement async operations for long-running tasks
- Add plugin system for custom commands