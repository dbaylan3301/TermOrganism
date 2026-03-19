#def run_in_sandbox(candidate, context=None):
#    return {
#        "ok": True,
#        "reason": "sandbox stub passed",
#        "candidate": candidate,
#    }

from __future__ import annotations


def run_in_sandbox(candidate, context=None):
    return {
        "ok": True,
        "reason": "sandbox stub passed",
        "candidate": candidate,
    }


class VerifierHub:
    def __init__(self):
        pass

    def verify(self, candidate, context=None):
        return run_in_sandbox(candidate, context)

    def run(self, candidate, context=None):
        return self.verify(candidate, context)
