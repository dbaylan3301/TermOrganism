from __future__ import annotations

import ast
import re

from core.experts.base import RepairExpert
from core.models.schemas import FailureContext, RepairCandidate
from core.util.diffing import unified_diff


class PythonSyntaxExpert(RepairExpert):
    name = "python_syntax"
    supported_languages = {"python"}

    def score(self, ctx: FailureContext) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0
        if ctx.language == "python":
            score += 0.35
            reasons.append("language=python")
        if "SyntaxError" in ctx.stderr:
            score += 0.45
            reasons.append("stderr contains SyntaxError")
        if "IndentationError" in ctx.stderr:
            score += 0.35
            reasons.append("stderr contains IndentationError")
        if "unterminated string literal" in ctx.stderr.lower():
            score += 0.25
            reasons.append("unterminated string literal signature")
        return min(score, 1.0), reasons

    def propose(self, ctx: FailureContext) -> list[RepairCandidate]:
        code = ctx.source_code
        proposals: list[tuple[str, str]] = []

        fixed_tabs = code.replace("\t", "    ")
        if fixed_tabs != code:
            proposals.append((fixed_tabs, "tabs replaced with spaces"))

        fixed_print = re.sub(r'^([ \t]*)print ([^\n]+)$', r'\1print(\2)', code, flags=re.MULTILINE)
        if fixed_print != code:
            proposals.append((fixed_print, "python2-style print converted to python3"))

        lines = code.splitlines()
        colon_fixed = []
        changed = False
        for line in lines:
            stripped = line.strip()
            if stripped and re.match(r'^(if|for|while|def|class|elif|else|try|except|with)\b', stripped):
                if not stripped.endswith(":"):
                    colon_fixed.append(line + ":")
                    changed = True
                    continue
            colon_fixed.append(line)
        if changed:
            proposals.append(("\n".join(colon_fixed) + ("\n" if code.endswith("\n") else ""), "missing block colons restored"))

        quote_fixed = self._close_unbalanced_quotes(code)
        if quote_fixed != code:
            proposals.append((quote_fixed, "unbalanced quotes closed heuristically"))

        unique: list[RepairCandidate] = []
        seen = set()
        for patched, rationale in proposals:
            if patched in seen:
                continue
            seen.add(patched)
            unique.append(
                RepairCandidate(
                    expert_name=self.name,
                    kind="syntax",
                    patched_code=patched,
                    patch_unified_diff=unified_diff(code, patched, ctx.file_path, ctx.file_path),
                    rationale=rationale,
                    expert_score=self._expert_confidence(code, patched),
                    patch_safety_score=self._patch_safety(code, patched),
                )
            )
        return unique

    def _close_unbalanced_quotes(self, code: str) -> str:
        single = code.count("'")
        double = code.count('"')
        if single % 2 == 1:
            return code + "\n'"
        if double % 2 == 1:
            return code + '\n"'
        return code

    def _expert_confidence(self, old: str, new: str) -> float:
        try:
            ast.parse(new)
            return 0.85 if old != new else 0.0
        except SyntaxError:
            return 0.35

    def _patch_safety(self, old: str, new: str) -> float:
        delta = abs(len(new) - len(old))
        return max(0.2, 1.0 - min(delta / 400.0, 0.8))
