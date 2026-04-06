from __future__ import annotations

from pathlib import Path
from typing import Any


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


def scan_repo(root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root or ".").resolve()
    readme = _readme_text(repo_root)
    readme_l = readme.lower()

    return {
        "repo_root": str(repo_root),
        "readme": readme,
        "has_tests": _exists_any(repo_root, "tests", "tests/*.py", "**/test_*.py", "**/*_test.py"),
        "has_ci": _exists_any(repo_root, ".github/workflows/*.yml", ".github/workflows/*.yaml"),
        "has_docs": _exists_any(repo_root, "docs", "docs/**", "mkdocs.yml", "mkdocs.yaml"),
        "has_examples": _exists_any(repo_root, "examples", "examples/**", "demo", "demo/**"),
        "has_pyproject": (repo_root / "pyproject.toml").exists(),
        "has_requirements": _exists_any(repo_root, "requirements.txt", "requirements-*.txt"),
        "has_changelog": _exists_any(repo_root, "CHANGELOG.md", "CHANGELOG.txt"),
        "has_contrib": _exists_any(repo_root, "CONTRIBUTING.md", ".github/ISSUE_TEMPLATE/**", ".github/pull_request_template.md"),
        "has_smoke": _exists_any(repo_root, "bin/*smoke*", "**/*smoke*"),
        "has_lsp": _exists_any(repo_root, "core/lsp/**", "editor/vscode/**", "editor/nvim/**"),
        "has_editor": _exists_any(repo_root, "editor/**"),
        "has_ollama": _exists_any(repo_root, "core/llm/**"),
        "has_chat": _exists_any(repo_root, "core/chat/**"),
        "has_watch": _exists_any(repo_root, "core/watch/**"),
        "has_daemon": _exists_any(repo_root, "core/daemon/**"),
        "has_install_doc": ("install" in readme_l) or ("kurulum" in readme_l),
        "has_arch_doc": ("architecture" in readme_l) or ("mimari" in readme_l) or ("design" in readme_l),
    }


def top_gaps(scan: dict[str, Any]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []

    if not scan["has_ci"]:
        gaps.append({
            "title": "CI hattı zayıf veya yok",
            "why": "Değişiklikler otomatik güvenlik süzgecinden geçmiyor olabilir.",
            "fix": "GitHub Actions ile py_compile + smoke + kritik acceptance akışları ekle.",
        })

    if not scan["has_tests"]:
        gaps.append({
            "title": "Test kapsamı eksik",
            "why": "Chat, routing, narrator ve proactive katmanlar kolay regress olabilir.",
            "fix": "Semantic router, repo assessment, fast_v2 seçimi ve narrator için deterministik testler ekle.",
        })

    if not scan["has_docs"]:
        gaps.append({
            "title": "Dokümantasyon katmanı zayıf",
            "why": "Sistem çok katmanlı; dışarıdan hızlı anlaşılması zor kalır.",
            "fix": "docs/ altında architecture, chat flow, proactive layer ve repair flow dökümleri ekle.",
        })

    if not scan["has_arch_doc"]:
        gaps.append({
            "title": "Mimari anlatım net değil",
            "why": "Bileşenler var ama veri akışı tek bakışta anlaşılmıyor.",
            "fix": "README içine core modules, data flow, routing ve Ollama rolü bölümü ekle.",
        })

    if not scan["has_examples"]:
        gaps.append({
            "title": "Örnek kullanım seti zayıf",
            "why": "Ürünün gerçek gücü hızlı sergilenemiyor.",
            "fix": "repo_summary, repo_gap, fast_v2, whisper, pre-save ve auto-fix demo örnekleri ekle.",
        })

    if not scan["has_contrib"]:
        gaps.append({
            "title": "Katkı akışı eksik",
            "why": "Büyüyen projede issue/PR standardı olmayınca bakım zorlaşır.",
            "fix": "CONTRIBUTING.md ve template dosyaları ekle.",
        })

    if not scan["has_changelog"]:
        gaps.append({
            "title": "Sürüm/değişim geçmişi görünür değil",
            "why": "Milestone ilerlemesi ve kırılma noktaları izlenmesi zorlaşır.",
            "fix": "CHANGELOG.md ile major değişimleri düzenli kaydet.",
        })

    if not (scan["has_pyproject"] or scan["has_requirements"]):
        gaps.append({
            "title": "Kurulum/paketleme standardı zayıf",
            "why": "Tekrarlanabilir kurulum zorlaşır.",
            "fix": "pyproject.toml veya net requirements yapısı ekle.",
        })

    if not scan["has_install_doc"]:
        gaps.append({
            "title": "Kurulum akışı net değil",
            "why": "Yeni kullanıcı hızlı başlayamayabilir.",
            "fix": "README başına quickstart ve 3 demo komutu ekle.",
        })

    if not scan["has_smoke"]:
        gaps.append({
            "title": "Acceptance smoke katmanı eksik",
            "why": "Görünen davranış kırıldığında bunu erken yakalamak zorlaşır.",
            "fix": "chat, pretty, repair ve proactive için acceptance smoke komutları ekle.",
        })

    return gaps


def repo_summary_text(scan: dict[str, Any]) -> str:
    parts = []
    parts.append("Bu repo, terminali bağlam farkındalıklı ve self-healing bir developer runtime haline getirmeye odaklanıyor.")
    features = []
    if scan["has_watch"]:
        features.append("predictive/watch katmanı")
    if scan["has_daemon"]:
        features.append("daemon tabanı")
    if scan["has_chat"]:
        features.append("chat/narration yüzeyi")
    if scan["has_lsp"] or scan["has_editor"]:
        features.append("editor/LSP entegrasyonu")
    if scan["has_ollama"]:
        features.append("yerel model/Ollama katmanı")
    if features:
        parts.append("Ana omurga: " + ", ".join(features) + ".")
    return " ".join(parts)


def architecture_review_text(scan: dict[str, Any]) -> str:
    strengths = []
    risks = []

    if scan["has_chat"]:
        strengths.append("chat/narrator yüzeyi oluşmuş")
    if scan["has_daemon"]:
        strengths.append("daemon + runtime katmanı mevcut")
    if scan["has_watch"]:
        strengths.append("predictive watch tarafı kurulmuş")
    if scan["has_editor"] or scan["has_lsp"]:
        strengths.append("editor entegrasyonu yönü açık")
    if not scan["has_tests"]:
        risks.append("test derinliği zayıf")
    if not scan["has_ci"]:
        risks.append("CI eksik")
    if not scan["has_docs"]:
        risks.append("dokümantasyon katmanı zayıf")

    out = []
    if strengths:
        out.append("Mimari güçlü taraflar: " + ", ".join(strengths) + ".")
    if risks:
        out.append("En kritik mimari riskler: " + ", ".join(risks) + ".")
    if not out:
        out.append("Belirgin mimari iskelet var, fakat dış görünümden kalite sertleştirme seviyesi sınırlı görünüyor.")
    return " ".join(out)


def weakness_analysis_text(scan: dict[str, Any]) -> str:
    weaknesses = []
    if not scan["has_tests"]:
        weaknesses.append("regression riski yüksek")
    if not scan["has_ci"]:
        weaknesses.append("otomatik doğrulama zayıf")
    if not scan["has_docs"]:
        weaknesses.append("sistemin anlaşılabilirliği düşük kalabilir")
    if not scan["has_examples"]:
        weaknesses.append("ürün gücü hızlı gösterilemiyor")
    if not weaknesses:
        return "Ana zayıflıklar temel iskelette değil, daha çok kalite sertleştirme ve geliştirici deneyimi tarafında."
    return "Bu repo şu an en çok şu alanlarda kırılgan görünüyor: " + ", ".join(weaknesses) + "."


def productization_text(scan: dict[str, Any]) -> str:
    return (
        "Ürünleşme için öncelik sırası: 1) install/quickstart netliği, 2) acceptance smoke + CI, "
        "3) chat ve repair için güvenilir demo senaryoları, 4) architecture/docs katmanı, 5) ölçülebilir kalite sinyalleri."
    )


def roadmap_text(scan: dict[str, Any]) -> str:
    return (
        "En stabil roadmap şu görünüyor: önce test/CI ve smoke sertleştirme, sonra semantic router ve chat UX kalitesi, "
        "ardından docs/productization, en son daha agresif automation ve multi-file intelligence."
    )


def test_strategy_text(scan: dict[str, Any]) -> str:
    return (
        "Test stratejisini üç katmana ayırmak doğru olur: unit (intent/router/spec), integration (chat/repair/proactive), "
        "acceptance smoke (pretty çıktılar, repo_gap, fast_v2, whisper/narrator davranışı)."
    )
