from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from core.policy.matcher import path_matches


@dataclass(slots=True)
class PolicyDecision:
    allow: bool
    reasons: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)


class PolicyEngine:
    def __init__(self, rules_path: str | Path = ".termorganism/rules/repo.yaml") -> None:
        self.rules_path = Path(rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        if not self.rules_path.exists():
            return {}
        return json.loads(self.rules_path.read_text(encoding="utf-8"))

    def evaluate(self, *, path: str, action: str, confidence: float) -> PolicyDecision:
        reasons: list[str] = []
        checks: list[str] = []

        for item in self.rules.get("deny_actions", []):
            if path_matches(path, item["pattern"]) and action in item.get("actions", []):
                reasons.append(f"action '{action}' blocked for {path}")
        for item in self.rules.get("min_confidence", []):
            if path_matches(path, item["pattern"]) and confidence < float(item["score"]):
                reasons.append(f"confidence {confidence:.2f} below {item['score']} for {path}")
        for item in self.rules.get("required_tests", []):
            if path_matches(path, item["pattern"]):
                checks.append(item["command"])

        return PolicyDecision(
            allow=(len(reasons) == 0),
            reasons=reasons,
            required_checks=checks,
        )
