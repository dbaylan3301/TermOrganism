from __future__ import annotations

import re


class DependencyExpert:
    name = "dependency"

    def _extract_missing_module(self, error_text: str) -> str | None:
        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        ]
        for pat in patterns:
            m = re.search(pat, error_text or "")
            if m:
                return m.group(1)
        return None

    def propose(self, context):
        error_text = getattr(context, "error_text", "") or ""
        missing = self._extract_missing_module(error_text)

        if not missing:
            return [{
                "expert": self.name,
                "confidence": 0.25,
                "summary": "Dependency issue suspected but missing package name could not be extracted",
                "patch": None,
                "candidate_code": "",
            }]

        return [{
            "expert": self.name,
            "confidence": 0.78,
            "summary": f"Missing dependency detected: {missing}",
            "patch": f"pip install {missing}",
            "candidate_code": "",
            "package": missing,
        }]
