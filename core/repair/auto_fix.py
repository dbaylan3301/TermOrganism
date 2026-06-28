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
