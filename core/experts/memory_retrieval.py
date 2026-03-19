class MemoryRetrievalExpert:
    name = "memory_retrieval"

    def propose(self, context):
        return [{
            "expert": self.name,
            "confidence": 0.35,
            "summary": "Retrieved similar repair memories",
            "patch": None,
        }]
