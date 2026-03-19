from __future__ import annotations

from core.experts.base import RepairExpert
from core.models.schemas import FailureContext, RepairCandidate


class ShellRuntimeExpert(RepairExpert):
    name = "shell_runtime"
    supported_languages = {"shell", "python"}

    def score(self, ctx: FailureContext) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0
        lowered = ctx.stderr.lower()
        if "permission denied" in lowered:
            score += 0.8
            reasons.append("permission denied")
        if "not executable" in lowered:
            score += 0.6
            reasons.append("not executable")
        if "env" in lowered or "path" in lowered:
            score += 0.2
            reasons.append("environment/path clue")
        return min(score, 1.0), reasons

    def propose(self, ctx: FailureContext) -> list[RepairCandidate]:
        lowered = ctx.stderr.lower()
        out: list[RepairCandidate] = []
        if "permission denied" in lowered:
            out.append(
                RepairCandidate(
                    expert_name=self.name,
                    kind="runtime",
                    patched_code=ctx.source_code,
                    patch_unified_diff="",
                    rationale="permission issue detected; suggest chmod or invoking interpreter explicitly",
                    expert_score=0.78,
                    patch_safety_score=0.98,
                    metadata={
                        "action": "suggest_runtime_fix",
                        "commands": [f"chmod +x {ctx.file_path}", f"python3 {ctx.file_path}"],
                    },
                )
            )
        return out
