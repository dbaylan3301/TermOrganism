from __future__ import annotations

from typing import Any

from core.chat.repo_assessment import (
    scan_repo,
    top_gaps,
    repo_summary_text,
    architecture_review_text,
    weakness_analysis_text,
    productization_text,
    roadmap_text,
    test_strategy_text,
)
from core.chat.task_spec import TaskSpec
from core.security.review import run_security_review, render_security_summary
from core.llm.mimo_brain import generate_natural_response


def _naturalize(answer: str, intent: str, message: str) -> str:
    natural = generate_natural_response(
        user_message=message,
        context={"intent": intent},
        intent=intent,
        data={"answer": answer},
    )
    if natural:
        return natural
    return answer


def _base_response(message: str, spec: TaskSpec, answer: str, *, root: str) -> dict[str, Any]:
    return {
        "ok": True,
        "intent": spec.intent_family,
        "confidence": spec.confidence,
        "message": message,
        "plan": [
            "inputu semantik olarak anlamlandıracağım",
            "repo bağlamını tarayıp en stabil yorumu seçeceğim",
            "sonucu kısa ve uygulanabilir şekilde döneceğim",
        ],
        "strategy_reason": f"TaskSpec route={spec.recommended_route} family={spec.intent_family}",
        "inference_reason": spec.user_goal,
        "answer": answer,
        "context": {
            "cwd": root,
            "repo_root": root,
            "git_branch": "-",
            "repo_type": "python_cli",
        },
        "reflective_pause": {
            "should_pause": spec.needs_execution,
            "force_preview": spec.needs_execution,
            "reason": "read-only semantic route" if not spec.needs_execution else "uygulama öncesi preview-first semantic route",
            "alternatives": [] if not spec.needs_execution else ["preview_only", "diagnose_first", "apply_safe_route"],
        },
        "intent_context": {
            "focus": "repo_assessment" if not spec.needs_execution else "safe_repair_intent",
            "confidence": spec.confidence,
            "branch": "-",
            "preload_routes": [spec.recommended_route, spec.intent_family, "semantic_grounding"],
            "modified_files": [],
        },
        "task_spec": spec.to_dict(),
    }


def build_semantic_response(message: str, spec: TaskSpec, repo_root: str | None = None) -> dict[str, Any] | None:
    if spec.needs_execution:
        return None

    scan = scan_repo(repo_root)
    root = str(scan["repo_root"])


    if spec.intent_family == "security_review":
        review = run_security_review(repo_root)
        resp = _base_response(message, spec, render_security_summary(review, mode="security_review"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "security_review"
        return resp

    if spec.intent_family == "secret_exposure_audit":
        review = run_security_review(repo_root, only={"secret_exposure"})
        resp = _base_response(message, spec, render_security_summary(review, mode="secret_exposure_audit"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "secret_exposure_audit"
        return resp

    if spec.intent_family == "dependency_risk_review":
        review = run_security_review(repo_root, only={"dependency_risk"})
        resp = _base_response(message, spec, render_security_summary(review, mode="dependency_risk_review"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "dependency_risk_review"
        return resp

    if spec.intent_family == "ci_cd_security_review":
        review = run_security_review(repo_root, only={"ci_cd_security"})
        resp = _base_response(message, spec, render_security_summary(review, mode="ci_cd_security_review"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "ci_cd_security_review"
        return resp

    if spec.intent_family == "config_misuse_review":
        review = run_security_review(repo_root, only={"config_misuse"})
        resp = _base_response(message, spec, render_security_summary(review, mode="config_misuse_review"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "config_misuse_review"
        return resp

    if spec.intent_family == "hardening_review":
        review = run_security_review(repo_root)
        resp = _base_response(message, spec, render_security_summary(review, mode="hardening_review"), root=root)
        resp["security_review"] = review
        resp["security_mode"] = "hardening_review"
        return resp

    if spec.intent_family == "repo_gap":
        gaps = top_gaps(scan)[:5]
        if gaps:
            answer = "Bu projede en kritik eksikler / zayıf alanlar şunlar görünüyor:\n\n" + "\n".join(
                f"{i}) {g['title']} — {g['why']} Çözüm: {g['fix']}"
                for i, g in enumerate(gaps, start=1)
            )
        else:
            answer = "Belirgin temel eksik görünmüyor; bundan sonraki seviye kalite sertleştirme ve dokümantasyon derinliği."
        answer = _naturalize(answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "repo_status":
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--short", "-b"],
                capture_output=True, text=True, timeout=10, cwd=root
            )
            if result.returncode == 0:
                lines = [x for x in result.stdout.splitlines() if x.strip()]
                if not lines:
                    raw_answer = "Repo temiz, değişiklik yok."
                else:
                    branch = lines[0][3:] if lines[0].startswith("## ") else "-"
                    modified = sum(1 for l in lines[1:] if "M " in l or l.startswith(" M"))
                    untracked = sum(1 for l in lines[1:] if l.startswith("??"))
                    raw_answer = f"Branch: {branch}\nDeğişiklik: {modified} dosya\nTakip edilmeyen: {untracked} dosya"
            else:
                raw_answer = "Git durumu alınamadı."
        except Exception:
            raw_answer = "Git durumu alınamadı."
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "repo_summary":
        raw_answer = repo_summary_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "architecture_review":
        raw_answer = architecture_review_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "weakness_analysis":
        raw_answer = weakness_analysis_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "productization":
        raw_answer = productization_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "roadmap":
        raw_answer = roadmap_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "test_strategy":
        raw_answer = test_strategy_text(scan)
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "help":
        raw_answer = (
            "Size nasıl yardımcı olabilirim? Repo özeti, test çalıştırma, "
            "dosya onarma gibi birçok işlem yapabilirim."
        )
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "diagnose":
        raw_answer = (
            "Sorunu teşhis ediyorum. En güvenli çözümü bulmaya çalışıyorum."
        )
        answer = _naturalize(raw_answer, spec.intent_family, message)
        return _base_response(message, spec, answer, root=root)

    if spec.intent_family == "general_analysis":
        answer = _naturalize("", spec.intent_family, message)
        if not answer:
            msg_lower = message.lower()
            if "merhaba" in msg_lower or "selam" in msg_lower:
                answer = "Merhaba! Ben TermOrganism. Size nasıl yardımcı olabilirim?"
            elif "nasıl" in msg_lower and ("yap" in msg_lower or "ol" in msg_lower):
                answer = "İsteğinizi anladım. En kısa yoldan çözmeye çalışıyorum."
            elif "nedir" in msg_lower or "ne" in msg_lower:
                answer = "Soruyu anladım. Kısa ve net bir açıklama yapacağım."
            else:
                answer = "Soruyu anladım. Size en kısa ve net yanıtı vermeye çalışacağım."
        return _base_response(message, spec, answer, root=root)

    return None
