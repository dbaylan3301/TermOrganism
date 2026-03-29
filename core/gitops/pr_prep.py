from __future__ import annotations


def build_pr_summary(*, title: str, summary: str, checks: list[str] | None = None) -> dict:
    return {
        "title": title,
        "summary": summary,
        "checks": checks or [],
    }
