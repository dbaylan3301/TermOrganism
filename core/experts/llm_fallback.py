class LLMFallbackExpert:
    name = "llm_fallback"

    def propose(self, context):
        return [{
            "expert": self.name,
            "confidence": 0.25,
            "summary": "Fallback heuristic proposal",
            "patch": None,
        }]
