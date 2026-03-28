from __future__ import annotations
from dataclasses import dataclass, field
from time import perf_counter

@dataclass
class LatencyMetrics:
    started_at: float = field(default_factory=perf_counter)
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = perf_counter()

    def elapsed_ms(self, start: str | None = None, end: str | None = None) -> float:
        s = self.started_at if start is None else self.marks[start]
        e = perf_counter() if end is None else self.marks[end]
        return round((e - s) * 1000, 3)

    def snapshot(self) -> dict[str, float]:
        out: dict[str, float] = {}
        prev_name = None
        prev_t = self.started_at
        for name, t in self.marks.items():
            out[f"{name}_ms"] = round((t - prev_t) * 1000, 3)
            prev_name = name
            prev_t = t
        out["total_ms"] = round((perf_counter() - self.started_at) * 1000, 3)
        return out
