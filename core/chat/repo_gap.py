from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_PATTERNS = [
    r"\bbu projede ne eksik\b",
    r"\bprojede ne eksik\b",
    r"\bprojede neler eksik\b",
    r"\brepoda ne eksik\b",
    r"\beksikler\b",
    r"\bhangi eksikler\b",
    r"\bwhat'?s missing\b",
    r"\bwhat is missing\b",
    r"\bmissing parts?\b",
    r"\bgaps?\b",
]


def looks_like_repo_gap_query(message: str) -> bool:
    text = " ".join(str(message or "").lower().split())
    return any(re.search(p, text) for p in _PATTERNS)


def _exists_any(root: Path, *patterns: str) -> bool:
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def _readme_text(root: Path) -> str:
    for name in ("README.md", "README.txt", "README.rst"):
        p = root / name
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")
    return ""


def _check_gaps(root: Path) -> list[dict[str, str]]:
    readme = _readme_text(root).lower()

    gaps: list[dict[str, str]] = []

    has_tests = _exists_any(root, "tests", "tests/*.py", "**/test_*.py", "**/*_test.py")
    has_ci = _exists_any(root, ".github/workflows/*.yml", ".github/workflows/*.yaml")
    has_docs = _exists_any(root, "docs", "docs/**", "mkdocs.yml", "mkdocs.yaml")
    has_examples = _exists_any(root, "examples", "examples/**", "demo", "demo/**")
    has_pyproject = (root / "pyproject.toml").exists()
    has_requirements = _exists_any(root, "requirements.txt", "requirements-*.txt")
    has_changelog = _exists_any(root, "CHANGELOG.md", "CHANGELOG.txt")
    has_contrib = _exists_any(root, "CONTRIBUTING.md", ".github/ISSUE_TEMPLATE/**", ".github/pull_request_template.md")
    has_smoke = _exists_any(root, "bin/*smoke*", "**/*smoke*")
    has_install_doc = ("install" in readme) or ("kurulum" in readme)
    has_arch_doc = ("architecture" in readme) or ("mimari" in readme) or ("design" in readme)

    if not has_ci:
        gaps.append({
            "title": "CI hattı zayıf veya yok",
            "why": "Repo değişiklikleri otomatik test/verify süzgecinden geçmiyor olabilir.",
            "fix": "GitHub Actions ile smoke + py_compile + kritik demo senaryolarını çalıştır.",
        })

    if not has_tests:
        gaps.append({
            "title": "Test kapsamı eksik",
            "why": "Chat, repair, proactive ve narrator akışları kolayca regress olabilir.",
            "fix": "Intent routing, repo_gap, fast_v2 seçimi ve whisper/narrator için küçük ama deterministik testler ekle.",
        })

    if not has_docs:
        gaps.append({
            "title": "Dokümantasyon katmanı zayıf",
            "why": "Özellikle chat UX, proactive layer ve route arbitration dışarıdan anlaşılması zor kalır.",
            "fix": "docs/ altında architecture, chat flow, repair flow ve proactive layer sayfaları ekle.",
        })

    if not has_arch_doc:
        gaps.append({
            "title": "Mimari anlatım yeterince açık değil",
            "why": "TermOrganism çok katmanlı bir sistem; bileşenlerin ilişkisi hızlı anlaşılmıyor.",
            "fix": "README içine 'core modules / data flow / route arbitration / Ollama role' bölümü ekle.",
        })

    if not has_examples:
        gaps.append({
            "title": "Örnek senaryo seti zayıf",
            "why": "Kullanıcı ürünün gerçek gücünü hızlı göremeyebilir.",
            "fix": "repo_summary, repo_gap, fast_v2 seçimi, pre-save, sidebar ve auto-fix için örnek kullanım dosyaları ekle.",
        })

    if not has_contrib:
        gaps.append({
            "title": "Katkı ve bakım akışı eksik",
            "why": "Büyüyen projede issue / PR standardı yoksa ileride kaos çıkar.",
            "fix": "CONTRIBUTING.md, issue templates ve PR template ekle.",
        })

    if not has_changelog:
        gaps.append({
            "title": "Değişim geçmişi görünür değil",
            "why": "Milestone bazlı ilerleme takip etmek zorlaşır.",
            "fix": "CHANGELOG.md ile chat, proactive, LSP, auto-fix ve Ollama entegrasyonu için sürüm notları tut.",
        })

    if not (has_pyproject or has_requirements):
        gaps.append({
            "title": "Paketleme/kurulum standardı eksik",
            "why": "Kurulum tekrarlanabilir değilse onboarding zorlaşır.",
            "fix": "pyproject.toml veya net requirements/constraints yapısı ekle.",
        })

    if not has_install_doc:
        gaps.append({
            "title": "Kurulum akışı yeterince net değil",
            "why": "Yeni kullanıcı hangi ortamda ne çalıştıracağını hızlı anlayamayabilir.",
            "fix": "README başına hızlı kurulum + quickstart + demo komutları ekle.",
        })

    if not has_smoke:
        gaps.append({
            "title": "Smoke/acceptance katmanı eksik",
            "why": "Ürünün görünen davranışı kırıldığında bunu erken yakalamak zorlaşır.",
            "fix": "chat, pretty, repair ve proactive için kısa acceptance smoke scriptleri ekle.",
        })

    return gaps


def build_repo_gap_response(message: str, repo_root: str | None = None) -> dict[str, Any] | None:
    if not looks_like_repo_gap_query(message):
        return None

    root = Path(repo_root or ".").resolve()
    gaps = _check_gaps(root)

    top = gaps[:5]
    if top:
        lines = []
        for i, item in enumerate(top, start=1):
            lines.append(f"{i}) {item['title']} — {item['why']} Çözüm: {item['fix']}")
        answer = (
            "Bu projede en kritik eksikler / zayıf alanlar şunlar görünüyor:\n\n"
            + "\n".join(lines)
        )
    else:
        answer = (
            "Belirgin bir temel eksik görünmüyor; bundan sonraki seviye daha çok kalite sertleştirme tarafı. "
            "Özellikle test derinliği, acceptance smoke ve dokümantasyon netliği daha da güçlendirilebilir."
        )

    return {
        "ok": True,
        "intent": "repo_gap",
        "confidence": 0.94,
        "message": message,
        "plan": [
            "repo yapısını ve dokümantasyonu tarayacağım",
            "yüksek etkili eksikleri ayıklayacağım",
            "en stabil geliştirme sırasını önereceğim",
        ],
        "strategy_reason": "classifier yerine repo-gap fast path uygulandı",
        "inference_reason": "soru doğrudan eksik/gap analizi istiyor",
        "answer": answer,
        "context": {
            "cwd": str(root),
            "repo_root": str(root),
            "git_branch": "-",
            "repo_type": "python_cli",
        },
        "reflective_pause": {
            "should_pause": False,
            "force_preview": False,
            "reason": "read-only repo gap analizi",
            "alternatives": [],
        },
        "intent_context": {
            "focus": "repo_assessment",
            "confidence": 0.91,
            "branch": "-",
            "preload_routes": ["repo_scan", "doc_scan", "gap_rank"],
            "modified_files": [],
        },
    }
