from __future__ import annotations


class PolicyRouter:
    def route(self, context):
        error_text = (getattr(context, "error_text", "") or "").lower()
        experts: list[str] = []

        if "syntaxerror" in error_text or "indentationerror" in error_text:
            experts.append("python_syntax")

        if "modulenotfounderror" in error_text or "no module named" in error_text:
            experts.append("dependency")

        if "filenotfounderror" in error_text or "no such file or directory" in error_text:
            experts.append("file_runtime")

        if (
            "permission denied" in error_text
            or "command not found" in error_text
            or "not found" in error_text
        ) and "no such file or directory" not in error_text:
            experts.append("shell_runtime")

        if not experts:
            experts.append("memory_retrieval")
            experts.append("llm_fallback")

        return experts


def route(context):
    return PolicyRouter().route(context)
