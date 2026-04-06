from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

__all__ = ["run_security_review", "render_security_summary"]

SKIP_DIRS = {
    ".git", ".venv", "venv", ".studio-venv", "site-packages", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox", ".eggs",
    "dist", "build", ".idea", ".vscode", "vendor", "third_party"
}

SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

CODE_PATTERNS = [
    ("config_misuse", "medium", r"shell\s*=\s*True", "subprocess shell=True kullanımı",
     "shell=False ve arg listesi kullan.",
     "shell=True komut enjeksiyonu ve beklenmeyen shell davranışı riskini artırır."),
    ("config_misuse", "medium", r"\beval\s*\(", "eval kullanımı",
     "eval yerine güvenli parser kullan.",
     "eval doğrudan yürütme yüzeyi açar."),
    ("config_misuse", "medium", r"\bexec\s*\(", "exec kullanımı",
     "exec yerine explicit dispatch kullan.",
     "exec dinamik kod yürütme riski üretir."),
    ("config_misuse", "medium", r"verify\s*=\s*False", "TLS doğrulaması kapatılmış",
     "verify=False kaldır.",
     "TLS doğrulamasını kapatmak MITM riskini artırır."),
    ("config_misuse", "low", r"debug\s*=\s*True", "Debug modu açık olabilir",
     "Prod ortamında debug kapat.",
     "Debug modu hata yüzeyini ve bilgi sızıntısını artırabilir."),
]

HIGH_RISK_FILENAMES = {
    ".env", ".env.local", ".env.prod", ".env.production",
    "secrets.yml", "secrets.yaml", "id_rsa", "id_ed25519",
    "package.json", "requirements.txt", "pyproject.toml",
}

CODE_GLOBS = [
    "*.py", "*.sh", "*.yml", "*.yaml", "*.json", "*.toml", "*.ini", "*.cfg", "*.conf"
]

WORKFLOW_GLOB = ".github/workflows/*.y*ml"


def _finding(
    *,
    kind: str,
    severity: str,
    title: str,
    evidence: str,
    file_path: str,
    remediation: str,
    why: str = "",
    confidence: float = 0.8,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "file_path": file_path,
        "remediation": remediation,
        "why": why,
        "confidence": round(float(confidence), 2),
    }


def _is_skipped(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except Exception:
        rel = path
    return any(part in SKIP_DIRS for part in rel.parts)


def _read_text(path: Path) -> str:
    try:
        if path.stat().st_size > 128_000:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _candidate_files(root: Path, *, mode: str) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()

    def add(p: Path):
        sp = str(p.resolve())
        if sp in seen:
            return
        seen.add(sp)
        out.append(p)

    if mode == "ci":
        wf_dir = root / ".github" / "workflows"
        if wf_dir.exists():
            for p in wf_dir.glob("*.y*ml"):
                if p.is_file():
                    add(p)
        return out[:40]

    if mode == "deps":
        wanted = {"requirements.txt", "pyproject.toml", "package.json"}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn in wanted:
                    p = Path(dirpath) / fn
                    add(p)
                    if len(out) >= 40:
                        return out[:40]
        return out[:40]

    if mode == "secrets":
        wanted_names = set(HIGH_RISK_FILENAMES)
        wanted_suffixes = {".env", ".pem", ".key", ".crt", ".py"}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                if fn in wanted_names or p.suffix.lower() in wanted_suffixes:
                    add(p)
                    if len(out) >= 180:
                        return out[:180]
        return out[:180]

    if mode == "config":
        wanted_suffixes = {".py", ".sh", ".yml", ".yaml", ".json", ".toml"}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.suffix.lower() in wanted_suffixes:
                    add(p)
                    if len(out) >= 220:
                        return out[:220]
        return out[:220]

    for sub in ["secrets", "deps", "ci", "config"]:
        for item in _candidate_files(root, mode=sub):
            add(item)
    return out[:320]


def _looks_secret_name(name: str) -> bool:
    n = str(name or "").lower()
    return any(x in n for x in [
        "api_key", "apikey", "secret", "token", "password", "passwd",
        "access_key", "private_key", "auth_token", "bearer"
    ])


def _looks_secret_value(value: str) -> bool:
    v = str(value or "").strip().strip('"').strip("'")
    if len(v) < 16:
        return False
    if v.lower() in {"true", "false", "none", "null"}:
        return False
    if v in {"tokenizer", "_TokenType", "TokenType", "token_type"}:
        return False
    has_digit = any(c.isdigit() for c in v)
    has_alpha = any(c.isalpha() for c in v)
    return has_alpha and (has_digit or any(c in "_-+/=" for c in v))


def _scan_secrets(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    explicit_patterns = [
        ("critical", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "Özel anahtar dosya içinde görünüyor"),
        ("high", r"ghp_[A-Za-z0-9]{20,}", "GitHub token benzeri değer görünüyor"),
        ("high", r"AKIA[0-9A-Z]{16}", "AWS access key benzeri değer görünüyor"),
    ]

    assign_pat = re.compile(r'(?im)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*[\'"]([^\'"]{16,})[\'"]')

    for p in _candidate_files(root, mode="secrets"):
        txt = _read_text(p)
        if not txt:
            continue

        matched = False
        for sev, pat, title in explicit_patterns:
            m = re.search(pat, txt)
            if m:
                findings.append(_finding(
                    kind="secret_exposure",
                    severity=sev,
                    title=title,
                    evidence=m.group(0)[:120],
                    file_path=str(p.relative_to(root)),
                    remediation="Secret'i repodan çıkar, rotate et ve env/secret manager kullan.",
                    why="Repoda duran gerçek credential veya private key yetkisiz erişime yol açabilir.",
                    confidence=0.9 if sev in {"critical", "high"} else 0.75,
                ))
                matched = True
                break
        if matched:
            continue

        for m in assign_pat.finditer(txt):
            name = m.group(1)
            value = m.group(2)
            if _looks_secret_name(name) and _looks_secret_value(value):
                findings.append(_finding(
                    kind="secret_exposure",
                    severity="medium",
                    title="Hardcoded credential benzeri atama görünüyor",
                    evidence=f"{name} = {value[:24]}...",
                    file_path=str(p.relative_to(root)),
                    remediation="Secret'i koda gömmek yerine env/secret manager kullan.",
                    why="Hardcoded sırlar commit geçmişi ve artefaktlar içinde sızabilir.",
                    confidence=0.72,
                ))
                break

        if p.name.lower() in {".env", ".env.local", ".env.prod", ".env.production"}:
            findings.append(_finding(
                kind="secret_exposure",
                severity="medium",
                title="Env dosyası repo içinde tutuluyor olabilir",
                evidence=p.name,
                file_path=str(p.relative_to(root)),
                remediation="Gerçek secret içeren env dosyalarını ignore et; yalnızca .env.example tut.",
                why="Repo içindeki env dosyaları yanlışlıkla paylaşılabilir.",
                confidence=0.70,
            ))

    return findings


def _scan_dependencies(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for p in _candidate_files(root, mode="deps"):
        txt = _read_text(p)
        if not txt:
            continue

        if p.name == "requirements.txt":
            for line in txt.splitlines():
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                if "@" in raw and ("git+" in raw or "http://" in raw or "https://" in raw):
                    findings.append(_finding(
                        kind="dependency_risk",
                        severity="medium",
                        title="VCS/URL tabanlı dependency kullanılıyor",
                        evidence=raw,
                        file_path=str(p.relative_to(root)),
                        remediation="Mümkünse yayınlanmış sürüm pinle.",
                        why="Harici URL veya VCS bağımlılıkları supply-chain riskini artırır.",
                        confidence=0.76,
                    ))
                elif not any(op in raw for op in ["==", "~=", "<=", ">=", "<", ">"]):
                    findings.append(_finding(
                        kind="dependency_risk",
                        severity="medium",
                        title="Pinlenmemiş Python dependency bulundu",
                        evidence=raw,
                        file_path=str(p.relative_to(root)),
                        remediation="Kritik dependency'leri sürüm aralığı veya exact pin ile sınırla.",
                        why="Pinlenmemiş bağımlılıklar beklenmeyen sürüm davranışı üretebilir.",
                        confidence=0.74,
                    ))

        elif p.name == "package.json":
            try:
                data = json.loads(txt)
            except Exception:
                data = {}
            for sec in ["dependencies", "devDependencies"]:
                deps = data.get(sec) or {}
                for name, ver in deps.items():
                    v = str(ver)
                    if v in {"*", "latest"}:
                        findings.append(_finding(
                            kind="dependency_risk",
                            severity="medium",
                            title="Node dependency sürümü gevşek",
                            evidence=f"{name}: {v}",
                            file_path=str(p.relative_to(root)),
                            remediation="Exact veya kontrollü range kullan.",
                            why="Gevşek sürüm aralıkları beklenmeyen paket güncellemelerine yol açabilir.",
                            confidence=0.79,
                        ))
                    elif v.startswith(("github:", "git+", "file:", "http://", "https://")):
                        findings.append(_finding(
                            kind="dependency_risk",
                            severity="medium",
                            title="Node dependency git/file/url kaynağından geliyor",
                            evidence=f"{name}: {v}",
                            file_path=str(p.relative_to(root)),
                            remediation="Registry sürümü tercih et.",
                            why="Harici kaynak dependency zinciri supply-chain riskini artırır.",
                            confidence=0.80,
                        ))

    return findings


def _scan_ci(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for wf in _candidate_files(root, mode="ci"):
        txt = _read_text(wf)
        if not txt:
            continue

        if "pull_request_target" in txt and "secrets." in txt:
            findings.append(_finding(
                kind="ci_cd_security",
                severity="high",
                title="pull_request_target ile secret erişimi bir arada görünüyor",
                evidence="pull_request_target + secrets",
                file_path=str(wf.relative_to(root)),
                remediation="PR kaynaklı workflow'larda secret kullanımını sınırla.",
                why="PR tetiklemelerinde secret erişimi privilege escalation riskini artırır.",
                confidence=0.86,
            ))

        if re.search(r"permissions:\s*write-all", txt):
            findings.append(_finding(
                kind="ci_cd_security",
                severity="high",
                title="Workflow geniş yazma yetkisi istiyor",
                evidence="permissions: write-all",
                file_path=str(wf.relative_to(root)),
                remediation="Permission'ları en düşük yetki ile tek tek tanımla.",
                why="Geniş CI yetkileri zincirleme hasar alanını büyütür.",
                confidence=0.84,
            ))

    return findings


def _scan_config_and_code(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for p in _candidate_files(root, mode="config"):
        txt = _read_text(p)
        if not txt:
            continue

        for kind, sev, pat, title, remediation, why in CODE_PATTERNS:
            m = re.search(pat, txt)
            if m:
                findings.append(_finding(
                    kind=kind,
                    severity=sev,
                    title=title,
                    evidence=m.group(0)[:120],
                    file_path=str(p.relative_to(root)),
                    remediation=remediation,
                    why=why,
                    confidence=0.75,
                ))
    return findings


def run_security_review(root: str | Path | None = None, only: set[str] | None = None) -> dict[str, Any]:
    repo_root = Path(root or ".").resolve()
    findings: list[dict[str, Any]] = []
    wanted = set(only or set())

    if not wanted or "secret_exposure" in wanted:
        findings.extend(_scan_secrets(repo_root))
    if not wanted or "dependency_risk" in wanted:
        findings.extend(_scan_dependencies(repo_root))
    if not wanted or "ci_cd_security" in wanted:
        findings.extend(_scan_ci(repo_root))
    if not wanted or "config_misuse" in wanted:
        findings.extend(_scan_config_and_code(repo_root))

    if only:
        findings = [f for f in findings if f["kind"] in only]

    findings.sort(
        key=lambda f: (SEV_RANK.get(str(f.get("severity", "low")), 0), float(f.get("confidence", 0.0))),
        reverse=True,
    )

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = str(f.get("severity", "low"))
        counts[sev] = counts.get(sev, 0) + 1

    overall = "low"
    if counts["critical"] or counts["high"]:
        overall = "high"
    elif counts["medium"]:
        overall = "medium"

    return {
        "repo_root": str(repo_root),
        "overall_risk": overall,
        "counts": counts,
        "findings": findings,
        "top_findings": findings[:5],
    }


def render_security_summary(review: dict[str, Any], *, mode: str = "security_review") -> str:
    top = list(review.get("top_findings") or [])
    counts = review.get("counts") or {}
    overall = review.get("overall_risk") or "low"

    header = (
        f"Güvenlik özeti: genel risk={overall}. "
        f"critical={counts.get('critical', 0)}, high={counts.get('high', 0)}, "
        f"medium={counts.get('medium', 0)}, low={counts.get('low', 0)}."
    )

    if not top:
        if mode == "hardening_review":
            return header + " Belirgin kritik bulgu görünmüyor; sonraki adım hardening checklist ve CI doğrulama katmanını güçlendirmek."
        return header + " Heuristik taramada belirgin bulgu çıkmadı; yine de manual review önerilir."

    if mode == "hardening_review":
        immediate = []
        this_week = []
        later = []

        for f in top:
            kind = str(f.get("kind", ""))
            sev = str(f.get("severity", "low"))
            line = f"- [{sev}] {f['title']} ({f['file_path']}) → {f['remediation']}"
            if kind in {"secret_exposure", "ci_cd_security"} or sev in {"critical", "high"}:
                immediate.append(line)
            elif kind in {"dependency_risk", "config_misuse"} or sev == "medium":
                this_week.append(line)
            else:
                later.append(line)

        parts = [header, ""]
        parts.append("Immediate fixes:")
        parts.extend(immediate or ["- Şu an için immediate sınıfında bulgu yok."])
        parts.append("")
        parts.append("This week:")
        parts.extend(this_week or ["- Bu hafta için ek orta seviye sertleştirme yok."])
        parts.append("")
        parts.append("Later:")
        parts.extend(later or ["- Daha sonra kalite ve görünürlük iyileştirmeleri yapılabilir."])
        return "\n".join(parts)

    lines = []
    for i, f in enumerate(top, start=1):
        piece = f"{i}) [{f['severity']}] {f['title']} — {f['evidence']} (dosya: {f['file_path']})"
        if f.get("why"):
            piece += f" Neden önemli: {f['why']}"
        piece += f" Çözüm: {f['remediation']}"
        lines.append(piece)

    return header + "\n\n" + "\n".join(lines)
