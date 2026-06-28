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